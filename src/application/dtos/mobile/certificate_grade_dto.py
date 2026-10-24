from pydantic import BaseModel, ConfigDict, Field

class CertificateGradeDto(BaseModel):
    """One subject row of a semester report (Zeugnis) from /me/certificates/grades."""
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    studentId: str | None = None
    certificateId: str | None = None
    gradeId: str | None = None
    profile: str | None = None
    semesterNo: str | None = None
    semesterId: str | None = None
    semesterTitle: str | None = None
    certificateType: str | None = None
    class_: str | None = Field(default=None, alias="class")
    promotionDecision: str | None = None
    promotionComment: str | None = None
    pointsMinus: str | None = None
    pointsPlus: str | None = None
    countInsufficient: str | None = None
    averageGrade: str | None = None
    absenceExcused: int | None = None
    absenceUnexcused: int | None = None
    subject: str | None = None
    grade: str | None = None
    label: str | None = None
    courseId: str | None = None
    gradeType: str | None = None
    gradeGroup: str | None = None
    gradesOrder: int | None = None
    certificateEntry: int | None = None
    datePublic: str | None = None
