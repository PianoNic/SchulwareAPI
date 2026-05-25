"""Class-based controller decorator for FastAPI.

Vendored from fastapi-utils 0.8.0 (MIT licensed, https://github.com/fastapiutils/fastapi-utils),
with the `typing_inspect.is_classvar` dependency replaced by a small inline check
against `typing.ClassVar` so we have zero external runtime deps for this module.

Usage:
    router = APIRouter(prefix="/api/foo", tags=["Foo"])

    @controller(router)
    class FooController:
        mediator: Mediator = Depends(get_mediator)   # class-level Depends

        @router.get("/bar")
        async def bar(self, request: Request):
            return await self.mediator.send(...)
"""

import inspect
from collections.abc import Callable
from typing import (
    Any,
    ClassVar,
    TypeVar,
    cast,
    get_origin,
    get_type_hints,
)

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute
from starlette.routing import Route, WebSocketRoute

T = TypeVar("T")

CONTROLLER_CLASS_KEY = "__controller_class__"
INCLUDE_INIT_PARAMS_KEY = "__include_init_params__"
RETURN_TYPES_FUNC_KEY = "__return_types_func__"


def _is_classvar(hint: Any) -> bool:
    return hint is ClassVar or get_origin(hint) is ClassVar


def controller(router: APIRouter, *urls: str) -> Callable[[type[T]], type[T]]:
    """
    Decorator that converts the decorated class into a class-based controller for the given router.

    Any methods decorated as endpoints using `router` will become endpoints in that router.
    The first positional argument (typically `self`) will be populated with an instance
    created via FastAPI's dependency injection, so class-level annotated attributes
    (e.g. ``mediator: Mediator = Depends(get_mediator)``) act as shared per-request deps.
    """

    def decorator(cls: type[T]) -> type[T]:
        return _build_controller(router, cls, *urls)

    return decorator


def _build_controller(router: APIRouter, cls: type[T], *urls: str, instance: Any = None) -> type[T]:
    _init_controller(cls, instance)
    _register_endpoints(router, cls, *urls)
    return cls


def _init_controller(cls: type[Any], instance: Any = None) -> None:
    """Idempotently rewrite `cls.__init__` so FastAPI can inject class-annotated dependencies."""
    if getattr(cls, CONTROLLER_CLASS_KEY, False):
        return  # already initialized
    old_init: Callable[..., Any] = cls.__init__
    old_signature = inspect.signature(old_init)
    old_parameters = list(old_signature.parameters.values())[1:]  # drop `self`
    new_parameters = [
        x for x in old_parameters
        if x.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]

    dependency_names: list[str] = []
    for name, hint in get_type_hints(cls).items():
        if _is_classvar(hint):
            continue
        parameter_kwargs = {"default": getattr(cls, name, Ellipsis)}
        dependency_names.append(name)
        new_parameters.append(
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=hint,
                **parameter_kwargs,
            )
        )
    new_signature = inspect.Signature(())
    if not instance or hasattr(cls, INCLUDE_INIT_PARAMS_KEY):
        new_signature = old_signature.replace(parameters=new_parameters)

    def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
        for dep_name in dependency_names:
            dep_value = kwargs.pop(dep_name)
            setattr(self, dep_name, dep_value)
        if instance and not hasattr(cls, INCLUDE_INIT_PARAMS_KEY):
            self.__class__ = instance.__class__
            self.__dict__ = instance.__dict__
        else:
            old_init(self, *args, **kwargs)

    setattr(cls, "__signature__", new_signature)
    setattr(cls, "__init__", new_init)
    setattr(cls, CONTROLLER_CLASS_KEY, True)


def _register_endpoints(router: APIRouter, cls: type[Any], *urls: str) -> None:
    inner_router = APIRouter()
    function_members = inspect.getmembers(cls, inspect.isfunction)
    for url in urls:
        _allocate_routes_by_method_name(router, url, function_members)
    router_roles = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            raise ValueError("The provided routes should be of type APIRoute")

        route_methods: Any = route.methods
        cast(tuple[Any], route_methods)
        router_roles.append((route.path, tuple(route_methods)))

    if len(set(router_roles)) != len(router_roles):
        raise Exception("An identical route role has been implemented more than once")

    functions_set = {func for _, func in function_members}
    controller_routes = [
        route for route in router.routes
        if isinstance(route, (Route, WebSocketRoute)) and route.endpoint in functions_set
    ]
    prefix_length = len(router.prefix)
    for route in controller_routes:
        router.routes.remove(route)
        route.path = route.path[prefix_length:]
        _update_route_endpoint_signature(cls, route)
        route.name = cls.__name__ + "." + route.name
        inner_router.routes.append(route)
    router.include_router(inner_router)


def _allocate_routes_by_method_name(
    router: APIRouter, url: str, function_members: list[tuple[str, Any]]
) -> None:
    existing_routes_endpoints: list[tuple[Any, str]] = [
        (route.endpoint, route.path) for route in router.routes if isinstance(route, APIRoute)
    ]
    for name, func in function_members:
        if hasattr(router, name) and not name.startswith("__") and not name.endswith("__"):
            if (func, url) not in existing_routes_endpoints:
                response_model = None
                responses = None
                kwargs = {}
                status_code = 200
                return_types_func = getattr(func, RETURN_TYPES_FUNC_KEY, None)
                if return_types_func:
                    response_model, status_code, responses, kwargs = return_types_func()

                api_resource = router.api_route(
                    url,
                    methods=[name.capitalize()],
                    response_model=response_model,
                    status_code=status_code,
                    responses=responses,
                    **kwargs,
                )
                api_resource(func)


def _update_route_endpoint_signature(cls: type[Any], route: Route | WebSocketRoute) -> None:
    """Fix the endpoint signature so FastAPI's DI resolves `self` via `Depends(cls)`."""
    old_endpoint = route.endpoint
    old_signature = inspect.signature(old_endpoint)
    old_parameters: list[inspect.Parameter] = list(old_signature.parameters.values())
    old_first_parameter = old_parameters[0]
    new_first_parameter = old_first_parameter.replace(default=Depends(cls))
    new_parameters = [new_first_parameter] + [
        parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY) for parameter in old_parameters[1:]
    ]

    new_signature = old_signature.replace(parameters=new_parameters)
    setattr(route.endpoint, "__signature__", new_signature)
