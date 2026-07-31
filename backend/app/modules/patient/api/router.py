"""HTTP routes for the Patient module.

Follows the pattern established in `app.modules.appointment.api.router`.
Covers `Patient` itself plus its six sub-resources (Contacts, Emergency
Contacts, Insurance, Allergies, Medications, Medical Conditions) — each
sub-resource gets `POST /patients/{patient_id}/<sub-resource>` (add) and
`GET /patients/{patient_id}/<sub-resource>` (list), plus
`GET /<sub-resource>/{id}` for direct lookup by the sub-resource's own
id (used e.g. by a client that already has a contact id from a prior
list call and doesn't want to re-fetch the whole patient's list).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ensure_same_organization
from app.api.pagination import Pagination, Sorting, paginate_and_sort
from app.api.search_params import SearchFilters, resolve_sort_field
from app.core.exceptions import NotFoundError
from app.modules.patient.api.dependencies import (
    get_add_emergency_contact_use_case,
    get_add_insurance_use_case,
    get_add_patient_contact_use_case,
    get_add_patient_medical_condition_use_case,
    get_add_patient_medication_use_case,
    get_emergency_contact_query_service,
    get_insurance_query_service,
    get_patient_allergy_query_service,
    get_patient_contact_query_service,
    get_patient_medical_condition_query_service,
    get_patient_medication_query_service,
    get_patient_query_service,
    get_record_patient_allergy_use_case,
    get_register_patient_use_case,
)
from app.modules.patient.api.schemas import (
    AddEmergencyContactRequest,
    AddInsuranceRequest,
    AddPatientContactRequest,
    AddPatientMedicalConditionRequest,
    AddPatientMedicationRequest,
    EmergencyContactResponse,
    InsuranceResponse,
    PatientAllergyResponse,
    PatientContactResponse,
    PatientMedicalConditionResponse,
    PatientMedicationResponse,
    PatientResponse,
    RecordPatientAllergyRequest,
    RegisterPatientRequest,
)
from app.modules.patient.application.dto import (
    AddEmergencyContactInput,
    AddInsuranceInput,
    AddPatientContactInput,
    AddPatientMedicalConditionInput,
    AddPatientMedicationInput,
    RecordPatientAllergyInput,
    RegisterPatientInput,
)
from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.application.services.patient_sub_resource_query_service import (
    EmergencyContactQueryService,
    InsuranceQueryService,
    PatientAllergyQueryService,
    PatientContactQueryService,
    PatientMedicalConditionQueryService,
    PatientMedicationQueryService,
)
from app.modules.patient.application.use_cases.add_emergency_contact import AddEmergencyContact
from app.modules.patient.application.use_cases.add_insurance import AddInsurance
from app.modules.patient.application.use_cases.add_patient_contact import AddPatientContact
from app.modules.patient.application.use_cases.add_patient_medical_condition import (
    AddPatientMedicalCondition,
)
from app.modules.patient.application.use_cases.add_patient_medication import (
    AddPatientMedication,
)
from app.modules.patient.application.use_cases.record_patient_allergy import (
    RecordPatientAllergy,
)
from app.modules.patient.application.use_cases.register_patient import RegisterPatient
from app.modules.patient.domain.enums import PatientStatus
from app.schemas.base import PaginatedResponse

router = APIRouter()

_SEARCH_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "first_name", "last_name", "patient_number", "status"}
)

PatientQS = Annotated[PatientQueryService, Depends(get_patient_query_service)]
ContactQS = Annotated[PatientContactQueryService, Depends(get_patient_contact_query_service)]
EmergencyContactQS = Annotated[
    EmergencyContactQueryService, Depends(get_emergency_contact_query_service)
]
InsuranceQS = Annotated[InsuranceQueryService, Depends(get_insurance_query_service)]
AllergyQS = Annotated[PatientAllergyQueryService, Depends(get_patient_allergy_query_service)]
MedicationQS = Annotated[
    PatientMedicationQueryService, Depends(get_patient_medication_query_service)
]
ConditionQS = Annotated[
    PatientMedicalConditionQueryService, Depends(get_patient_medical_condition_query_service)
]

RegisterUseCase = Annotated[RegisterPatient, Depends(get_register_patient_use_case)]
AddContactUseCase = Annotated[AddPatientContact, Depends(get_add_patient_contact_use_case)]
AddEmergencyContactUseCase = Annotated[
    AddEmergencyContact, Depends(get_add_emergency_contact_use_case)
]
AddInsuranceUseCase = Annotated[AddInsurance, Depends(get_add_insurance_use_case)]
RecordAllergyUseCase = Annotated[RecordPatientAllergy, Depends(get_record_patient_allergy_use_case)]
AddMedicationUseCase = Annotated[AddPatientMedication, Depends(get_add_patient_medication_use_case)]
AddConditionUseCase = Annotated[
    AddPatientMedicalCondition, Depends(get_add_patient_medical_condition_use_case)
]


# --- Patient -----------------------------------------------------------


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    body: RegisterPatientRequest,
    use_case: RegisterUseCase,
    query_service: PatientQS,
    current_user: CurrentUser,
) -> PatientResponse:
    output = await use_case.execute(
        RegisterPatientInput(
            organization_id=current_user.organization_id,
            **body.model_dump(),
            created_by=current_user.user_id,
        )
    )
    summary = await query_service.get_patient_summary(output.patient_id)
    assert summary is not None
    return PatientResponse.model_validate(summary)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID, query_service: PatientQS, current_user: CurrentUser
) -> PatientResponse:
    summary = await query_service.get_patient_summary(patient_id)
    if summary is None:
        raise NotFoundError(f"no patient found with id {patient_id}")
    response = PatientResponse.model_validate(summary)
    ensure_same_organization(response.organization_id, current_user)
    return response


@router.get("", response_model=PaginatedResponse[PatientResponse])
async def search_patients(
    query_service: PatientQS,
    pagination: Pagination,
    sorting: Sorting,
    filters: SearchFilters,
    current_user: CurrentUser,
    status_filter: Annotated[list[PatientStatus] | None, Query(alias="status")] = None,
) -> PaginatedResponse[PatientResponse]:
    """Search & Filtering module: organization-scoped, database-backed
    search/filter/sort/paginate over patients — see
    `PatientRepository.search`'s docstring for how `filters.q` combines
    full-text and partial matching."""
    sort_field = resolve_sort_field(
        sorting.sort_by, allowed_sort_fields=_SEARCH_SORT_FIELDS, default_field="created_at"
    )
    summaries, total = await query_service.search_patients(
        organization_id=current_user.organization_id,
        query=filters.q,
        statuses=status_filter,
        created_from=filters.created_from,
        created_to=filters.created_to,
        updated_from=filters.updated_from,
        updated_to=filters.updated_to,
        include_deleted=filters.include_deleted,
        sort_by=sort_field,
        sort_order=sorting.sort_order,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    items = [PatientResponse.model_validate(s) for s in summaries]
    return PaginatedResponse(
        items=items, total=total, offset=pagination.offset, limit=pagination.limit
    )


# --- Contacts ------------------------------------------------------------


@router.post("/{patient_id}/contacts", response_model=PatientContactResponse, status_code=201)
async def add_patient_contact(
    patient_id: UUID,
    body: AddPatientContactRequest,
    use_case: AddContactUseCase,
    query_service: ContactQS,
    current_user: CurrentUser,
) -> PatientContactResponse:
    output = await use_case.execute(
        AddPatientContactInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_contact_summary(output.contact_id)
    assert summary is not None
    return PatientContactResponse.model_validate(summary)


@router.get("/{patient_id}/contacts", response_model=PaginatedResponse[PatientContactResponse])
async def list_patient_contacts(
    patient_id: UUID,
    query_service: ContactQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientContactResponse]:
    summaries = await query_service.list_contacts_for_patient(patient_id)
    items = [PatientContactResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"contact_type", "is_primary"}),
    )


# --- Emergency Contacts ----------------------------------------------------


@router.post(
    "/{patient_id}/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=201,
)
async def add_emergency_contact(
    patient_id: UUID,
    body: AddEmergencyContactRequest,
    use_case: AddEmergencyContactUseCase,
    query_service: EmergencyContactQS,
    current_user: CurrentUser,
) -> EmergencyContactResponse:
    output = await use_case.execute(
        AddEmergencyContactInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_contact_summary(output.contact_id)
    assert summary is not None
    return EmergencyContactResponse.model_validate(summary)


@router.get(
    "/{patient_id}/emergency-contacts",
    response_model=PaginatedResponse[EmergencyContactResponse],
)
async def list_emergency_contacts(
    patient_id: UUID,
    query_service: EmergencyContactQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[EmergencyContactResponse]:
    summaries = await query_service.list_contacts_for_patient(patient_id)
    items = [EmergencyContactResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"full_name", "priority", "is_primary"}),
    )


# --- Insurance -----------------------------------------------------------


@router.post("/{patient_id}/insurance", response_model=InsuranceResponse, status_code=201)
async def add_insurance(
    patient_id: UUID,
    body: AddInsuranceRequest,
    use_case: AddInsuranceUseCase,
    query_service: InsuranceQS,
    current_user: CurrentUser,
) -> InsuranceResponse:
    output = await use_case.execute(
        AddInsuranceInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_insurance_summary(output.insurance_id)
    assert summary is not None
    return InsuranceResponse.model_validate(summary)


@router.get("/{patient_id}/insurance", response_model=PaginatedResponse[InsuranceResponse])
async def list_insurance(
    patient_id: UUID,
    query_service: InsuranceQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[InsuranceResponse]:
    summaries = await query_service.list_insurance_for_patient(patient_id)
    items = [InsuranceResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"provider_name", "expiry_date", "status"}),
    )


# --- Allergies -----------------------------------------------------------


@router.post("/{patient_id}/allergies", response_model=PatientAllergyResponse, status_code=201)
async def record_patient_allergy(
    patient_id: UUID,
    body: RecordPatientAllergyRequest,
    use_case: RecordAllergyUseCase,
    query_service: AllergyQS,
    current_user: CurrentUser,
) -> PatientAllergyResponse:
    output = await use_case.execute(
        RecordPatientAllergyInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_allergy_summary(output.allergy_id)
    assert summary is not None
    return PatientAllergyResponse.model_validate(summary)


@router.get("/{patient_id}/allergies", response_model=PaginatedResponse[PatientAllergyResponse])
async def list_patient_allergies(
    patient_id: UUID,
    query_service: AllergyQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientAllergyResponse]:
    summaries = await query_service.list_allergies_for_patient(patient_id)
    items = [PatientAllergyResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"allergen_name", "severity", "status"}),
    )


# --- Medications ---------------------------------------------------------


@router.post("/{patient_id}/medications", response_model=PatientMedicationResponse, status_code=201)
async def add_patient_medication(
    patient_id: UUID,
    body: AddPatientMedicationRequest,
    use_case: AddMedicationUseCase,
    query_service: MedicationQS,
    current_user: CurrentUser,
) -> PatientMedicationResponse:
    output = await use_case.execute(
        AddPatientMedicationInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_medication_summary(output.medication_id)
    assert summary is not None
    return PatientMedicationResponse.model_validate(summary)


@router.get(
    "/{patient_id}/medications", response_model=PaginatedResponse[PatientMedicationResponse]
)
async def list_patient_medications(
    patient_id: UUID,
    query_service: MedicationQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientMedicationResponse]:
    summaries = await query_service.list_medications_for_patient(patient_id)
    items = [PatientMedicationResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"medication_name", "is_current", "start_date"}),
    )


# --- Medical Conditions ----------------------------------------------------


@router.post(
    "/{patient_id}/medical-conditions",
    response_model=PatientMedicalConditionResponse,
    status_code=201,
)
async def add_patient_medical_condition(
    patient_id: UUID,
    body: AddPatientMedicalConditionRequest,
    use_case: AddConditionUseCase,
    query_service: ConditionQS,
    current_user: CurrentUser,
) -> PatientMedicalConditionResponse:
    output = await use_case.execute(
        AddPatientMedicalConditionInput(
            patient_id=patient_id, **body.model_dump(), created_by=current_user.user_id
        )
    )
    summary = await query_service.get_condition_summary(output.condition_id)
    assert summary is not None
    return PatientMedicalConditionResponse.model_validate(summary)


@router.get(
    "/{patient_id}/medical-conditions",
    response_model=PaginatedResponse[PatientMedicalConditionResponse],
)
async def list_patient_medical_conditions(
    patient_id: UUID,
    query_service: ConditionQS,
    pagination: Pagination,
    sorting: Sorting,
    current_user: CurrentUser,
) -> PaginatedResponse[PatientMedicalConditionResponse]:
    summaries = await query_service.list_conditions_for_patient(patient_id)
    items = [PatientMedicalConditionResponse.model_validate(s) for s in summaries]
    return paginate_and_sort(
        items,
        pagination=pagination,
        sorting=sorting,
        allowed_sort_fields=frozenset({"condition_name", "severity", "status"}),
    )
