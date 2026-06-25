from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    """
    Service xử lý nghiệp vụ liên quan đến Patient.

    Tối ưu thiết kế:
    - Router không trực tiếp viết nhiều query database.
    - Gom logic normalize/tìm kiếm/phân trang ở một nơi.
    - Dùng joinedload cho quan hệ nhiều-một để giảm số query.
    """

    def __init__(self, db: Session):
        """
        db là database session được FastAPI inject từ dependency get_db().
        """

        self.db = db

    def get_by_id(
        self,
        patient_id: UUID,
        *,
        current_user: User,
    ) -> Patient | None:
        """
        Lấy bệnh nhân theo ID trong phạm vi được phép của user hiện tại.

        Admin được truy cập mọi hồ sơ. Bác sĩ chỉ được truy cập hồ sơ do
        chính mình tạo.
        """

        statement = select(Patient).where(Patient.id == patient_id)
        statement = self._scope_to_current_user(statement, current_user)
        return self.db.scalar(statement)

    def get_detail_by_id(
        self,
        patient_id: UUID,
        *,
        current_user: User,
    ) -> Patient | None:
        """
        Lấy chi tiết bệnh nhân kèm người tạo trong phạm vi được phép.

        Vì model relationship dùng lazy='raise',
        ta phải chủ động eager-load relationship cần dùng.
        """

        statement = (
            select(Patient)
            .options(joinedload(Patient.created_by_user))
            .where(Patient.id == patient_id)
        )
        statement = self._scope_to_current_user(statement, current_user)

        return self.db.scalar(statement)

    def get_by_patient_code(
        self,
        patient_code: str,
        *,
        current_user: User,
    ) -> Patient | None:
        """
        Lấy bệnh nhân theo mã trong phạm vi được phép của user hiện tại.

        Mã bệnh nhân được chuẩn hóa uppercase để tìm kiếm nhất quán.
        """

        normalized_code = patient_code.strip().upper()

        statement = select(Patient).where(
            Patient.patient_code == normalized_code
        )
        statement = self._scope_to_current_user(statement, current_user)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        data: PatientCreate,
        created_by_user: User,
    ) -> Patient:
        """
        Tạo hồ sơ bệnh nhân mới.

        created_by_user lấy từ tài khoản đang đăng nhập,
        không lấy từ request frontend để tránh giả mạo người tạo.
        """

        patient = Patient(
            full_name=data.full_name,
            date_of_birth=data.date_of_birth,
            sex=data.sex,
            phone_number=data.phone_number,
            notes=data.notes,
            created_by=created_by_user.id,
        )

        self.db.add(patient)

        try:
            # Flush để PostgreSQL sinh patient_code và trả mã về ngay trong
            # response/audit log.
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Could not create a unique patient code") from exc

        return patient

    def update(
        self,
        *,
        patient: Patient,
        data: PatientUpdate,
    ) -> Patient:
        """
        Cập nhật hồ sơ bệnh nhân.

        Chỉ cập nhật các field frontend gửi lên.
        Không cho đổi patient_code để giữ mã bệnh nhân ổn định.
        """

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(patient, field, value)

        self.db.flush()
        return patient

    def list_patients(
        self,
        *,
        current_user: User,
        pagination: PaginationParams,
        keyword: str | None = None,
        created_by: UUID | None = None,
    ) -> PaginatedResponse[Patient]:
        """
        Lấy danh sách bệnh nhân có phân trang.

        keyword tìm theo:
        - patient_code
        - full_name
        - phone_number

        Admin có thể lọc theo created_by. Bác sĩ luôn bị giới hạn về chính
        current_user.id, bất kể query parameter frontend gửi lên.
        """

        filters = []

        if current_user.role == UserRole.doctor:
            filters.append(Patient.created_by == current_user.id)

        if keyword:
            normalized_keyword = f"%{keyword.strip()}%"
            normalized_code_keyword = f"%{keyword.strip().upper()}%"

            filters.append(
                or_(
                    Patient.patient_code.ilike(normalized_code_keyword),
                    Patient.full_name.ilike(normalized_keyword),
                    Patient.phone_number.ilike(normalized_keyword),
                )
            )

        if current_user.role == UserRole.admin and created_by is not None:
            filters.append(Patient.created_by == created_by)

        total_statement = select(func.count()).select_from(Patient)

        list_statement = (
            select(Patient)
            .order_by(Patient.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )

        if filters:
            total_statement = total_statement.where(*filters)
            list_statement = list_statement.where(*filters)

        total = self.db.scalar(total_statement) or 0
        items = list(self.db.scalars(list_statement).all())

        return PaginatedResponse[Patient].create(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    def _scope_to_current_user(self, statement, current_user: User):
        """
        Thêm điều kiện sở hữu vào query bệnh nhân.

        Trả về None ở các hàm get nếu bác sĩ yêu cầu ID ngoài phạm vi, giúp
        endpoint trả 404 và không tiết lộ hồ sơ đó có tồn tại hay không.
        """

        if current_user.role == UserRole.doctor:
            statement = statement.where(Patient.created_by == current_user.id)

        return statement
