from pydantic import BaseModel, Field


class IngestDocument(BaseModel):
    doc_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: list[IngestDocument]


class IngestResponse(BaseModel):
    collection: str
    tenant_id: str
    points_upserted: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResult(BaseModel):
    score: float
    doc_id: str
    chunk_id: str
    text: str
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    collection: str
    tenant_id: str
    count: int
    results: list[SearchResult]


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    tenant_id: str
    answer: str
    sources: list[SearchResult]


class DispatchRoute(BaseModel):
    route_id: str = Field(min_length=1)
    route_name: str = Field(min_length=1)
    start_point: str = Field(default="")
    end_point: str = Field(default="")
    stops_count: int = Field(default=0, ge=0)


class DispatchDriver(BaseModel):
    driver_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: str = Field(default="AVAILABLE")
    recent_assignments_count: int = Field(default=0, ge=0)


class DispatchVehicle(BaseModel):
    vehicle_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    number_plate: str = Field(min_length=1)
    status: str = Field(default="AVAILABLE")
    fuel_percentage: int = Field(default=100, ge=0, le=100)
    recent_assignments_count: int = Field(default=0, ge=0)


class DispatchCopilotRequest(BaseModel):
    routes: list[DispatchRoute] = Field(default_factory=list)
    drivers: list[DispatchDriver] = Field(default_factory=list)
    vehicles: list[DispatchVehicle] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=20)


class DispatchCopilotSuggestion(BaseModel):
    rank: int
    score: float
    route_id: str
    route_name: str
    driver_id: str
    driver_name: str
    vehicle_id: str
    vehicle_name: str
    vehicle_number_plate: str
    reasoning: list[str] = Field(default_factory=list)


class DispatchCopilotResponse(BaseModel):
    tenant_id: str
    plan_id: str = ""
    suggestions: list[DispatchCopilotSuggestion]
    unmatched_route_ids: list[str] = Field(default_factory=list)


class DispatchCopilotApproveRequest(BaseModel):
    suggestions: list[DispatchCopilotSuggestion] = Field(default_factory=list)
    plan_id: str = ""
    route_ids: list[str] = Field(default_factory=list)
    scheduled_at: str = Field(min_length=1)


class DispatchCopilotApprovedAssignment(BaseModel):
    route_id: str
    route_name: str
    driver_id: str
    driver_name: str
    vehicle_id: str
    vehicle_name: str
    vehicle_number_plate: str
    scheduled_at: str


class DispatchCopilotApproveResponse(BaseModel):
    tenant_id: str
    plan_id: str = ""
    approved: int
    assignments: list[DispatchCopilotApprovedAssignment] = Field(default_factory=list)


class DocumentUpdateRequest(BaseModel):
    text: str = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)


class DocumentMutationResponse(BaseModel):
    collection: str
    tenant_id: str
    doc_id: str
    points_affected: int


class AsyncIngestResponse(BaseModel):
    job_id: str
    status: str
    tenant_id: str


class AsyncIngestStatusResponse(BaseModel):
    job_id: str
    status: str
    tenant_id: str
    points_upserted: int = 0
    error: str | None = None
