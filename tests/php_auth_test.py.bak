import requests
import re

def get_php_session_id(full_url: str) -> str | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0",
    }

    try:
        response = requests.get(full_url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        set_cookie_headers = response.headers.get("Set-Cookie")

        if set_cookie_headers:
            match = re.search(r"PHPSESSID=([^;]+)", set_cookie_headers)
            if match:
                return match.group(1)
            else:
                print("PHPSESSID not found in Set-Cookie header.")
                return None
        else:
            print("No 'Set-Cookie' header found in the response.")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        print(f"Response content: {response.text[:200]}...")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occurred: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"The request timed out: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    # Your full URL
    url = "https://schulnetz.bbbaden.ch/?code="

    session_id = get_php_session_id(url)

    if session_id:
        print(f"Extracted PHPSESSID: {session_id}")
    else:
        print("Failed to extract PHPSESSID.")