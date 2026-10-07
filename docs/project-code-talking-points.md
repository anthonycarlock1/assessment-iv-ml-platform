# Assessment IV: simple code talking points

This guide covers the project-owned files in `assessment-iv-ml-platform`. Each file has short speaking notes for its main blocks. Links point to the source; line numbers were updated after adding inline comments.

Installed packages, caches, virtual environments, build output, Git internals, logs, local environment files, and Terraform state are summarized at the end rather than treated as application source. Binary model and image files are explained by purpose. No AWS command needs to be run to use this guide.

## Start with the full request path

1. The React dashboard collects the user’s input and calls `/api`.
2. Nginx serves the built dashboard and forwards API traffic to the gateway.
3. The gateway chooses exactly one service: fraud, forecasting, or recommendations.
4. FastAPI validates the request and passes it to the inference engine.
5. In the deployed adapters, the engine calls SageMaker through a replaceable runtime client.
6. Inside SageMaker, the hosting container loads the saved model and runs the actual model calculation.
7. The result returns through the same path and appears in the dashboard.

**Important distinction:** local model execution inside the SageMaker hosting container is the real hosted inference calculation. It is different from silently falling back to a model on the frontend or EKS adapter. Offline tests deliberately use local artifacts or replacement clients.

## Vocabulary for presenting

- **Gateway:** the front desk that sends a request to the correct service.
- **Adapter:** the Python API that turns a business request into a model-runtime request.
- **Artifact:** the saved, already-trained model file.
- **Deployment:** Kubernetes instructions for running and replacing application pods.
- **Service:** a stable network address for the application’s changing pods.
- **ConfigMap:** ordinary settings, such as endpoint names and region.
- **Pod Identity:** the AWS role supplied to a workload without embedding access keys.
- **Health:** whether the process responds. **Readiness:** whether required configuration or local artifacts are available.
- **Request:** a CPU/memory reservation used when scheduling. **Limit:** a cap on container resource use.

## Finding a file quickly

Use **Cmd+F** (Mac) or **Ctrl+F** and search the complete path, such as `k8s/deployments/fraud.yaml` or `apps/services/common/api.py`. Each file is listed once in alphabetical folder order. Source links jump to the block being explained.

## File-by-file notes

### `.dockerignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `.github/workflows/ci-cd.yml`

GitHub Actions automation: runs when code is pushed or a pull request is opened.

- **[Triggers](../.github/workflows/ci-cd.yml#L4):** Defines the branches/events that start this workflow.
- **[Jobs](../.github/workflows/ci-cd.yml#L10):** Lists the runner jobs and their steps.
- **[Checkout](../.github/workflows/ci-cd.yml#L16):** Downloads the repository into the runner.
- **[Python](../.github/workflows/ci-cd.yml#L20):** Installs the required Python interpreter.
- **[Dependencies](../.github/workflows/ci-cd.yml#L26):** Installs the project libraries.
- **[Tests](../.github/workflows/ci-cd.yml#L33):** Runs the Python suite, including routing and inference checks.

- **[Frontend environment](../.github/workflows/ci-cd.yml#L39):** Installs Node 22 for building the dashboard.
- **[Frontend checks](../.github/workflows/ci-cd.yml#L44):** Installs locked dependencies and runs build, lint, and polling tests.
- **[Nginx checks](../.github/workflows/ci-cd.yml#L54):** Builds a local frontend image and proves missing assets affect readiness without breaking liveness.
- **[Terraform installer](../.github/workflows/ci-cd.yml#L60):** Downloads a pinned Terraform executable for the runner’s OS/CPU.
- **[Infrastructure syntax](../.github/workflows/ci-cd.yml#L81):** Initializes providers without a backend and checks Terraform configuration; this does not apply infrastructure.
- **[Deployment gate](../.github/workflows/ci-cd.yml#L88):** Runs only after validation passes and only for pushes to the main/master branch.
- **[AWS access](../.github/workflows/ci-cd.yml#L104):** Uses GitHub repository secrets to authenticate the runner. This differs from Pod Identity inside EKS.
- **[Container release](../.github/workflows/ci-cd.yml#L115):** Builds images using the Git commit hash as the release tag.
- **[Workload release](../.github/workflows/ci-cd.yml#L127):** Runs the tested deploy script against the existing cluster.

### `.github/workflows/ci.yml`

GitHub Actions automation: runs when code is pushed or a pull request is opened.

- **[Triggers](../.github/workflows/ci.yml#L4):** Defines the branches/events that start this workflow.
- **[Jobs](../.github/workflows/ci.yml#L10):** Lists the runner jobs and their steps.
- **[Checkout](../.github/workflows/ci.yml#L16):** Downloads the repository into the runner.
- **[Python](../.github/workflows/ci.yml#L20):** Installs the required Python interpreter.
- **[Dependencies](../.github/workflows/ci.yml#L26):** Installs the project libraries.
- **[Tests](../.github/workflows/ci.yml#L33):** Runs the Python suite, including routing and inference checks.

- **[Optional Terraform check](../.github/workflows/ci.yml#L39):** Validates infrastructure syntax only if Terraform is installed; otherwise reports a skip.

### `.github/workflows/smoke-tests.yml`

GitHub Actions automation: runs when code is pushed or a pull request is opened.

- **[Triggers](../.github/workflows/smoke-tests.yml#L4):** Defines the branches/events that start this workflow.
- **[Jobs](../.github/workflows/smoke-tests.yml#L10):** Lists the runner jobs and their steps.
- **[Checkout](../.github/workflows/smoke-tests.yml#L15):** Downloads the repository into the runner.
- **[Python](../.github/workflows/smoke-tests.yml#L19):** Installs the required Python interpreter.
- **[Dependencies](../.github/workflows/smoke-tests.yml#L32):** Installs the project libraries.
- **[Tests](../.github/workflows/smoke-tests.yml#L35):** Runs the Python suite, including routing and inference checks.

- **[Dependency cache](../.github/workflows/smoke-tests.yml#L25):** Reuses downloaded Python packages between runner jobs.

### `.gitignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `PLAN.md`

Project documentation, not running application code.

- **Reading notes:** Records project planning notes, which can include earlier intentions rather than current deployed state.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `README.md`

Project documentation, not running application code.

- **Reading notes:** Explains setup, the main commands, and project use; the frontend README also retains starter-tool guidance.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `apps/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/gateway/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../apps/gateway/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../apps/gateway/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../apps/gateway/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../apps/gateway/Dockerfile#L9):** Includes the shared service implementation.
- **[Port](../apps/gateway/Dockerfile#L11):** Documents the port served by this image.
- **[Launch](../apps/gateway/Dockerfile#L14):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `apps/gateway/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/gateway/main.py`

Routes frontend API traffic to exactly the requested downstream service.

- **[Imports and setup](../apps/gateway/main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[downstream](../apps/gateway/main.py#L19):** Sends one HTTP request to a downstream API using an explicit timeout.
- **[proxy](../apps/gateway/main.py#L25):** Builds the selected service URL, forwards the request ID, and converts downstream/network failures into safe gateway responses.
- **[health](../apps/gateway/main.py#L41):** Reports gateway process liveness without depending on the downstream APIs.
- **[ready](../apps/gateway/main.py#L47):** Checks service URL configuration and all downstream readiness responses; reports 503 when any required service is unavailable.
- **[register](../apps/gateway/main.py#L57):** Creates prediction, health, readiness, and metadata routes for one specific service.
- **[register → predict](../apps/gateway/main.py#L59):** Rejects non-finite JSON and forwards this service’s prediction request.
- **[register → health](../apps/gateway/main.py#L63):** Forwards only this service’s health check.
- **[register → ready](../apps/gateway/main.py#L66):** Forwards only this service’s readiness check.
- **[register → metadata](../apps/gateway/main.py#L69):** Forwards only this service’s metadata request.
- **[Service addresses](../apps/gateway/main.py#L11):** Reads each downstream URL from configuration, with cross-namespace Service DNS defaults.
- **[Register all services](../apps/gateway/main.py#L77):** Installs the four routes for fraud, forecasting, and recommendations.


### `apps/gateway/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `apps/gateway/test_main.py`

Automated tests for this part of the platform.

- **[Imports and setup](../apps/gateway/test_main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_route_targets_only_correct_service](../apps/gateway/test_main.py#L12):** Checks every service/path combination and proves exactly one call went to the intended downstream URL, carrying the request ID.
- **[test_downstream_errors](../apps/gateway/test_main.py#L26):** Checks that input errors keep the appropriate status and backend failures become safe gateway errors.
- **[test_health_and_readiness](../apps/gateway/test_main.py#L34):** Checks gateway liveness, all-service readiness, and safe errors when downstream connections fail.

### `apps/services/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/services/common/__init__.py`

Marks this directory as a Python package so modules can be imported.

- Package setup lives here; application behavior is defined in the service modules.

### `apps/services/common/api.py`

Shared HTTP layer used by all three inference APIs.

- **[Imports and setup](../apps/services/common/api.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[ServiceMetadata](../apps/services/common/api.py#L15):** Defines the typed operational response: service, owning team, model/version, release, provider, endpoint, and region.
- **[create_app](../apps/services/common/api.py#L28):** Builds the shared FastAPI application, attaches the engine, and installs logging and validation handlers.
- **[create_app → metadata](../apps/services/common/api.py#L37):** Returns configured service/model information without invoking AWS. Missing values remain missing rather than becoming demo data.
- **[create_app → health](../apps/services/common/api.py#L48):** Returns process liveness. It does not invoke SageMaker or check the model service.
- **[create_app → ready](../apps/services/common/api.py#L54):** Returns readiness only when required configuration or a local artifact is available; otherwise returns 503.
- **[create_app → predict](../apps/services/common/api.py#L62):** Validates the engine result against the response model. It checks forecast length and recommendation consistency, then maps bad input and downstream failures into safe HTTP errors.
- **[Typed route registration](../apps/services/common/api.py#L88):** Attaches the service-specific request type to the common function and registers a typed `/predict` response.


### `apps/services/common/inference.py`

Chooses remote invocation or actual saved-model calculation, and prepares model-specific features.

- **[Imports and setup](../apps/services/common/inference.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[InferenceEngine](../apps/services/common/inference.py#L11):** Keeps model loading and feature preparation separate from HTTP handling.
- **[InferenceEngine → __init__](../apps/services/common/inference.py#L15):** Stores the provider/model path and injected adapter. Local mode loads the artifact and recommendation catalog; failed loading makes readiness fail.
- **[InferenceEngine → ready](../apps/services/common/inference.py#L35):** Checks remote endpoint/region configuration, or whether the local model was loaded.
- **[InferenceEngine → predict](../apps/services/common/inference.py#L42):** In SageMaker mode, invokes AWS and labels the result remote. In local mode, prepares fraud fields, iterates forecast lags, or ranks recommendation candidates by probability.
- **[Fraud calculation](../apps/services/common/inference.py#L46):** Uses the model’s class prediction and probability of the fraud class.
- **[Forecast calculation](../apps/services/common/inference.py#L53):** Reverses the latest history into lag 1/2/3, pads short history, and appends each new forecast before predicting again.
- **[Recommendation calculation](../apps/services/common/inference.py#L70):** Filters the catalog by category, scores candidate items, sorts highest probability first, and returns up to the requested limit.


### `apps/services/common/observability.py`

Shared request IDs and structured logging.

- **[Imports and setup](../apps/services/common/observability.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[instrument](../apps/services/common/observability.py#L19):** Installs shared middleware that adds a request ID and writes one JSON record for each completed HTTP request.
- **[instrument → context](../apps/services/common/observability.py#L23):** Validates or generates the request ID, measures duration, adds the ID to the response, and logs service/team/path/status/duration.

### `apps/services/common/sagemaker_adapter.py`

The boundary between Python inference APIs and AWS SageMaker Runtime.

- **[Imports and setup](../apps/services/common/sagemaker_adapter.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[RuntimeFailure](../apps/services/common/sagemaker_adapter.py#L11):** Represents an inference-runtime problem without exposing the original AWS details to the caller.
- **[RuntimeInputRejected](../apps/services/common/sagemaker_adapter.py#L15):** Distinguishes input rejected by the hosted model from an unavailable runtime.
- **[SageMakerRuntimeAdapter](../apps/services/common/sagemaker_adapter.py#L20):** Wraps AWS invocation so tests can supply a fake client instead of calling AWS.
- **[SageMakerRuntimeAdapter → __init__](../apps/services/common/sagemaker_adapter.py#L22):** Reads endpoint and region from arguments/environment and accepts an optional fake client.
- **[SageMakerRuntimeAdapter → is_configured](../apps/services/common/sagemaker_adapter.py#L29):** Checks that an endpoint name and AWS region are present.
- **[SageMakerRuntimeAdapter → client](../apps/services/common/sagemaker_adapter.py#L35):** Creates the SageMaker Runtime client only when needed, with explicit connect/read timeouts and automatic SDK retries disabled.
- **[SageMakerRuntimeAdapter → log_failure](../apps/services/common/sagemaker_adapter.py#L43):** Writes a structured error event containing service/team, exception type, and AWS error code; excludes raw AWS messages and stack traces.
- **[SageMakerRuntimeAdapter → invoke_with_retry](../apps/services/common/sagemaker_adapter.py#L50):** Sends the serialized request. Retries once after 250 ms only for a fast no-response/model-not-ready failure; skips slow failures and ordinary request/permission errors.
- **[SageMakerRuntimeAdapter → invoke](../apps/services/common/sagemaker_adapter.py#L72):** Requires valid configuration, converts the payload to JSON, reads and closes the response stream, and wraps invalid responses or AWS failures in safe exceptions.
- **[get_runtime_adapter](../apps/services/common/sagemaker_adapter.py#L98):** Creates a runtime adapter for the selected service, using optional region/endpoint arguments or environment settings.

### `apps/services/common/schemas.py`

Business request and response contracts enforced by Pydantic.

- **[Imports and setup](../apps/services/common/schemas.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[Input](../apps/services/common/schemas.py#L7):** Rejects extra fields and non-finite numbers, so requests cannot contain unexpected data, NaN, or Infinity.
- **[Transaction](../apps/services/common/schemas.py#L11):** Defines the fraud inputs: amount, transaction count, and account age; all must be nonnegative.
- **[ForecastRequest](../apps/services/common/schemas.py#L17):** Requires a history of numbers and a bounded number of future periods.
- **[RecommendationRequest](../apps/services/common/schemas.py#L22):** Requires a positive user ID, a category, and a bounded result limit.
- **[Output](../apps/services/common/schemas.py#L28):** Adds the model name and states whether inference came from local execution or SageMaker.
- **[FraudResponse](../apps/services/common/schemas.py#L34):** Allows only fraud/legitimate labels and a risk score between zero and one.
- **[ForecastResponse](../apps/services/common/schemas.py#L39):** Defines the predicted values and the number of periods.
- **[Recommendation](../apps/services/common/schemas.py#L44):** Defines one recommended item, its category, and its score.
- **[RecommendationResponse](../apps/services/common/schemas.py#L50):** Groups ranked items under the requested user ID.

### `apps/services/common/test_sagemaker_adapter.py`

Automated tests for this part of the platform.

- **[Imports and setup](../apps/services/common/test_sagemaker_adapter.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_environment_and_injected_runtime](../apps/services/common/test_sagemaker_adapter.py#L10):** Checks that endpoint/region come from configuration and that a supplied fake AWS client receives the expected JSON request.
- **[test_requires_endpoint_and_region](../apps/services/common/test_sagemaker_adapter.py#L20):** Checks that missing critical runtime configuration prevents invocation.
- **[test_client_timeouts](../apps/services/common/test_sagemaker_adapter.py#L29):** Checks the explicit AWS connect/read timeout settings.
- **[test_invalid_runtime_response](../apps/services/common/test_sagemaker_adapter.py#L40):** Rejects malformed JSON and non-object runtime responses.
- **[test_aws_failure_wrapped](../apps/services/common/test_sagemaker_adapter.py#L46):** Checks that an AWS failure becomes a safe runtime exception.
- **[test_failure_log_is_structured_and_does_not_leak_aws_message](../apps/services/common/test_sagemaker_adapter.py#L54):** Checks the logged error fields and confirms private AWS messages are omitted.
- **[test_fast_unavailable_model_retries_once_and_returns_semantic_output](../apps/services/common/test_sagemaker_adapter.py#L72):** Simulates a fast transient failure followed by success and checks the returned forecast values and identical retry payload.
- **[test_slow_unavailable_model_does_not_retry_past_gateway_budget](../apps/services/common/test_sagemaker_adapter.py#L84):** Checks that a slow failure does not trigger an extra request beyond the gateway budget.
- **[test_model_unavailable_retry_is_bounded](../apps/services/common/test_sagemaker_adapter.py#L93):** Checks that repeated unavailability stops after two attempts.

### `apps/services/common/validation.py`

Shared safe handling of malformed request data.

- **[Imports and setup](../apps/services/common/validation.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[install_validation_handler](../apps/services/common/validation.py#L11):** Registers a 422 error handler that returns field locations and explanations without echoing unsafe raw input.
- **[install_validation_handler → invalid_request](../apps/services/common/validation.py#L14):** Turns Pydantic validation failures into JSON-safe field error details.
- **[require_finite_json](../apps/services/common/validation.py#L22):** Walks nested dictionaries/lists and rejects NaN or Infinity before forwarding a request.

### `apps/services/forecasting/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../apps/services/forecasting/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../apps/services/forecasting/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../apps/services/forecasting/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../apps/services/forecasting/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../apps/services/forecasting/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../apps/services/forecasting/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../apps/services/forecasting/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `apps/services/forecasting/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/services/forecasting/main.py`

Small entry point for the forecasting API.

- **[Imports](../apps/services/forecasting/main.py#L2):** Uses the shared HTTP application factory.
- **[Contracts](../apps/services/forecasting/main.py#L4):** Selects this service’s request and response models.
- **[Application](../apps/services/forecasting/main.py#L8):** Builds this service with common metadata, health, readiness, logging, validation, and prediction behavior.

### `apps/services/forecasting/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `apps/services/forecasting/test_main.py`

Automated tests for this part of the platform.

- **[Imports and setup](../apps/services/forecasting/test_main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_health_and_ready](../apps/services/forecasting/test_main.py#L8):** Checks that the service is alive and its local test model is ready.
- **[test_real_prediction](../apps/services/forecasting/test_main.py#L14):** Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just HTTP 200.

### `apps/services/fraud/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../apps/services/fraud/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../apps/services/fraud/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../apps/services/fraud/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../apps/services/fraud/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../apps/services/fraud/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../apps/services/fraud/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../apps/services/fraud/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `apps/services/fraud/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/services/fraud/main.py`

Small entry point for the fraud API.

- **[Imports](../apps/services/fraud/main.py#L2):** Uses the shared HTTP application factory.
- **[Contracts](../apps/services/fraud/main.py#L4):** Selects this service’s request and response models.
- **[Application](../apps/services/fraud/main.py#L8):** Builds this service with common metadata, health, readiness, logging, validation, and prediction behavior.

### `apps/services/fraud/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `apps/services/fraud/test_main.py`

Automated tests for this part of the platform.

- **[Imports and setup](../apps/services/fraud/test_main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_health_and_ready](../apps/services/fraud/test_main.py#L8):** Checks that the service is alive and its local test model is ready.
- **[test_real_prediction](../apps/services/fraud/test_main.py#L14):** Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just HTTP 200.

### `apps/services/recommendations/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../apps/services/recommendations/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../apps/services/recommendations/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../apps/services/recommendations/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../apps/services/recommendations/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../apps/services/recommendations/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../apps/services/recommendations/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../apps/services/recommendations/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `apps/services/recommendations/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `apps/services/recommendations/main.py`

Small entry point for the recommendations API.

- **[Imports](../apps/services/recommendations/main.py#L2):** Uses the shared HTTP application factory.
- **[Contracts](../apps/services/recommendations/main.py#L4):** Selects this service’s request and response models.
- **[Application](../apps/services/recommendations/main.py#L8):** Builds this service with common metadata, health, readiness, logging, validation, and prediction behavior.

### `apps/services/recommendations/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `apps/services/recommendations/test_main.py`

Automated tests for this part of the platform.

- **[Imports and setup](../apps/services/recommendations/test_main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_health_and_ready](../apps/services/recommendations/test_main.py#L8):** Checks that the service is alive and its local test model is ready.
- **[test_real_prediction](../apps/services/recommendations/test_main.py#L14):** Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just HTTP 200.

### `dashboard/frontend/.gitignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `dashboard/frontend/.oxlintrc.json`

JSON configuration or recorded verification evidence.

- **Schema/plugins:** enables React-aware lint checks.
- **rules:** treats invalid hook usage as an error and configures component-export warnings.

### `dashboard/frontend/Dockerfile`

Recipe for building this component’s container image.

- **[Build stage](../dashboard/frontend/Dockerfile#L2):** Uses Node to install frontend dependencies and compile the React app.
- **[Dependency install](../dashboard/frontend/Dockerfile#L6):** Installs the exact versions in the lockfile.
- **[Compile](../dashboard/frontend/Dockerfile#L9):** Creates static production HTML, JavaScript, and CSS.
- **[Serving stage](../dashboard/frontend/Dockerfile#L11):** Uses a smaller nginx image to serve the compiled app.
- **[Configuration](../dashboard/frontend/Dockerfile#L13):** Installs the API proxy and health/readiness configuration.
- **[Assets](../dashboard/frontend/Dockerfile#L15):** Copies build output into nginx’s web directory.
- **[Port](../dashboard/frontend/Dockerfile#L17):** Documents port 80.

### `dashboard/frontend/README.md`

Project documentation, not running application code.

- **Reading notes:** Explains setup, the main commands, and project use; the frontend README also retains starter-tool guidance.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `dashboard/frontend/index.html`

Project support configuration.

- **[Page metadata](../dashboard/frontend/index.html#L4):** Defines document metadata/title/icon references.
- **[React mount point](../dashboard/frontend/index.html#L12):** Provides the element where React renders the dashboard.
- **[Entry script](../dashboard/frontend/index.html#L14):** Loads src/main.jsx for the Vite build/development flow.

### `dashboard/frontend/nginx.conf`

Production web server and same-origin API proxy.

- **[Server/root](../dashboard/frontend/nginx.conf#L3):** Listens on port 80 and serves compiled frontend files.
- **[Liveness](../dashboard/frontend/nginx.conf#L6):** Responds when nginx is running; it does not call AWS.
- **[Readiness](../dashboard/frontend/nginx.conf#L8):** Returns 503 if the frontend index page is missing.
- **[API forwarding](../dashboard/frontend/nginx.conf#L15):** Sends API traffic to the gateway in platform-team, with explicit timeouts and request-ID forwarding.
- **[SPA routes](../dashboard/frontend/nginx.conf#L22):** Serves real files when present, otherwise the app’s index page for client-side navigation.

### `dashboard/frontend/package-lock.json`

JSON configuration or recorded verification evidence.

- **Root package:** records the frontend’s direct dependencies.
- **packages / resolved / integrity:** records the complete dependency tree, download locations, and checksums so npm ci can reproduce installation. This generated tree is not custom application logic.

### `dashboard/frontend/package.json`

JSON configuration or recorded verification evidence.

- **[Commands](../dashboard/frontend/package.json#L6):** Defines dev, build, lint, preview, and polling-test commands.
- **[Application libraries](../dashboard/frontend/package.json#L13):** Provides React and ReactDOM.
- **[Build tools](../dashboard/frontend/package.json#L17):** Provides Vite, the React plugin, linting, and type definitions.

### `dashboard/frontend/public/favicon.svg`

Visual asset or screenshot, not executable application code.

- **Purpose:** Provides an icon or starter visual asset; a file’s presence does not mean the current App.jsx uses it.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `dashboard/frontend/public/icons.svg`

Visual asset or screenshot, not executable application code.

- **Purpose:** Provides an icon or starter visual asset; a file’s presence does not mean the current App.jsx uses it.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `dashboard/frontend/src/App.css`

Stylesheet controlling appearance and responsive layout.

- **[.platform-shell](../dashboard/frontend/src/App.css#L2):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[.service-meta](../dashboard/frontend/src/App.css#L22):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.topbar](../dashboard/frontend/src/App.css#L27):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.topbar h1](../dashboard/frontend/src/App.css#L35):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.topbar-actions](../dashboard/frontend/src/App.css#L42):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.topbar-meta](../dashboard/frontend/src/App.css#L48):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.eyebrow](../dashboard/frontend/src/App.css#L54):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.eyebrow--accent](../dashboard/frontend/src/App.css#L63):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.action-button](../dashboard/frontend/src/App.css#L68):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[.action-button:hover](../dashboard/frontend/src/App.css#L80):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[.content](../dashboard/frontend/src/App.css#L86):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.hero-panel](../dashboard/frontend/src/App.css#L93):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.hero-copy](../dashboard/frontend/src/App.css#L103):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-copy h2](../dashboard/frontend/src/App.css#L108):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-copy p](../dashboard/frontend/src/App.css#L115):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-summary](../dashboard/frontend/src/App.css#L122):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-summary div](../dashboard/frontend/src/App.css#L133):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-summary span](../dashboard/frontend/src/App.css#L140):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.hero-summary strong](../dashboard/frontend/src/App.css#L148):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.metrics-grid](../dashboard/frontend/src/App.css#L154):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.metric-card](../dashboard/frontend/src/App.css#L161):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.metric-card__label](../dashboard/frontend/src/App.css#L171):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[.metric-card__value](../dashboard/frontend/src/App.css#L179):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.metric-card__change](../dashboard/frontend/src/App.css#L187):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.panel-grid](../dashboard/frontend/src/App.css#L195):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.panel-grid--bottom](../dashboard/frontend/src/App.css#L202):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.panel](../dashboard/frontend/src/App.css#L207):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.panel-header](../dashboard/frontend/src/App.css#L215):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.panel-header h3](../dashboard/frontend/src/App.css#L222):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.muted](../dashboard/frontend/src/App.css#L228):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.service-list](../dashboard/frontend/src/App.css#L234):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.service-row](../dashboard/frontend/src/App.css#L241):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.service-row--healthy](../dashboard/frontend/src/App.css#L252):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.service-row--offline](../dashboard/frontend/src/App.css#L258):** Styles status text/badges so availability and errors are readable.
- **[.service-row strong](../dashboard/frontend/src/App.css#L264):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.service-row span](../dashboard/frontend/src/App.css#L271):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.service-row small](../dashboard/frontend/src/App.css#L277):** Sets spacing, panel appearance, and the arrangement of this layout block.
- **[.service-meta](../dashboard/frontend/src/App.css#L285):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.status-pill](../dashboard/frontend/src/App.css#L291):** Styles status text/badges so availability and errors are readable.
- **[.status-pill--online](../dashboard/frontend/src/App.css#L304):** Styles status text/badges so availability and errors are readable.
- **[.status-pill--offline](../dashboard/frontend/src/App.css#L311):** Styles status text/badges so availability and errors are readable.
- **[.status-pill--pending](../dashboard/frontend/src/App.css#L318):** Styles status text/badges so availability and errors are readable.
- **[.latency](../dashboard/frontend/src/App.css#L325):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-list](../dashboard/frontend/src/App.css#L332):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-card](../dashboard/frontend/src/App.css#L339):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-card h4](../dashboard/frontend/src/App.css#L347):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-block](../dashboard/frontend/src/App.css#L353):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-block strong](../dashboard/frontend/src/App.css#L362):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.result-block--empty](../dashboard/frontend/src/App.css#L367):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.pipeline-list](../dashboard/frontend/src/App.css#L372):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.pipeline-list li](../dashboard/frontend/src/App.css#L382):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.pipeline-list li span](../dashboard/frontend/src/App.css#L390):** Sets typography, color, spacing, or appearance for this named UI element.
- **[.pipeline-list p](../dashboard/frontend/src/App.css#L403):** Sets typography, color, spacing, or appearance for this named UI element.
- **[@media (max-width: 900px)](../dashboard/frontend/src/App.css#L410):** Adjusts columns and stacking for smaller screens.
- **[@media (max-width: 640px)](../dashboard/frontend/src/App.css#L422):** Adjusts columns and stacking for smaller screens.
- **[.prediction-grid](../dashboard/frontend/src/App.css#L444):** Wraps long response or endpoint text to keep it readable.
- **[form](../dashboard/frontend/src/App.css#L446):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[label](../dashboard/frontend/src/App.css#L448):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[input](../dashboard/frontend/src/App.css#L450):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[pre](../dashboard/frontend/src/App.css#L452):** Wraps long response or endpoint text to keep it readable.
- **[button:disabled](../dashboard/frontend/src/App.css#L454):** Styles form inputs, labels, buttons, and disabled/busy controls.
- **[.operation-status](../dashboard/frontend/src/App.css#L457):** Styles status text/badges so availability and errors are readable.
- **[.operation-status small](../dashboard/frontend/src/App.css#L459):** Styles status text/badges so availability and errors are readable.
- **[.endpoint](../dashboard/frontend/src/App.css#L461):** Wraps long response or endpoint text to keep it readable.
- **Starter selectors:** some older metric/pipeline styles remain available but are not rendered by the current App.jsx.

### `dashboard/frontend/src/App.jsx`

The actual React dashboard: operational status above, small live prediction forms below.

- **[Service/form definitions](../dashboard/frontend/src/App.jsx#L7):** Lists friendly service names and sample form inputs. These are request examples, not saved model results.
- **[API base](../dashboard/frontend/src/App.jsx#L13):** Uses a configured API base or same-origin `/api`.
- **[Request helper](../dashboard/frontend/src/App.jsx#L16):** Fetches JSON with a timeout/cancellation, reads request IDs, and turns API errors into visible messages.
- **[Form state](../dashboard/frontend/src/App.jsx#L23):** Keeps editable inputs, results, errors, elapsed time, and busy state separate for each service.
- **[Submit block](../dashboard/frontend/src/App.jsx#L31):** Converts text inputs into the business payload, rejects empty forecast values, and sends the correct prediction request.
- **[Form rendering](../dashboard/frontend/src/App.jsx#L46):** Builds labeled inputs and a submit button, then shows the actual response, elapsed time, provider, and request ID.
- **[Operations card](../dashboard/frontend/src/App.jsx#L66):** Displays API-supplied team, health, readiness, model/release versions, provider, endpoint, and region. Missing data and errors stay visible.
- **[Dashboard state](../dashboard/frontend/src/App.jsx#L93):** Stores each service/check separately and keeps a reference to the active poller.
- **[Polling lifecycle](../dashboard/frontend/src/App.jsx#L98):** Starts independent background checks, merges each response immediately, and stops/aborts checks when the component unmounts.
- **[Page layout](../dashboard/frontend/src/App.jsx#L76):** Renders the header, manual refresh button, service operations cards, and three independent prediction forms.

### `dashboard/frontend/src/assets/hero.png`

Visual asset or screenshot, not executable application code.

- **Purpose:** Provides an icon or starter visual asset; a file’s presence does not mean the current App.jsx uses it.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `dashboard/frontend/src/assets/react.svg`

Visual asset or screenshot, not executable application code.

- **Purpose:** Provides an icon or starter visual asset; a file’s presence does not mean the current App.jsx uses it.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `dashboard/frontend/src/assets/vite.svg`

Visual asset or screenshot, not executable application code.

- **Purpose:** Provides an icon or starter visual asset; a file’s presence does not mean the current App.jsx uses it.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `dashboard/frontend/src/index.css`

Stylesheet controlling appearance and responsive layout.

- **[Global theme](../dashboard/frontend/src/index.css#L2):** Sets fonts, colors, line height, and text rendering.
- **[Box sizing](../dashboard/frontend/src/index.css#L15):** Makes element widths include padding and borders.
- **[Page defaults](../dashboard/frontend/src/index.css#L24):** Removes default margin and supplies the background/minimum height.
- **[Shared controls](../dashboard/frontend/src/index.css#L31):** Uses the same font across form controls.
- **[Image sizing](../dashboard/frontend/src/index.css#L39):** Keeps images within their containers.
- **[App root](../dashboard/frontend/src/index.css#L45):** Makes the application fill the page height.

### `dashboard/frontend/src/main.jsx`

Project support configuration.

- **[Imports](../dashboard/frontend/src/main.jsx#L2):** Loads React, global styles, and the dashboard component.
- **[Mount](../dashboard/frontend/src/main.jsx#L8):** Finds the root HTML element and renders the dashboard.
- **[Development checks](../dashboard/frontend/src/main.jsx#L11):** Enables React’s extra development lifecycle checks; polling cleanup prevents duplicate lingering checks.

### `dashboard/frontend/src/polling.js`

Independent polling so one service cannot delay the entire dashboard.

- **[Poller setup](../dashboard/frontend/src/polling.js#L3):** Creates separate tasks for health, readiness, and metadata for each service.
- **[One check](../dashboard/frontend/src/polling.js#L8):** Skips overlapping requests, starts a cancellable five-second check, and immediately reports loading, success, or error.
- **[Reschedule](../dashboard/frontend/src/polling.js#L20):** After the check completes, schedules that same check again; the default pause is 15 seconds.
- **[Manual refresh](../dashboard/frontend/src/polling.js#L26):** Starts idle checks without duplicating checks already running.
- **[Cleanup](../dashboard/frontend/src/polling.js#L29):** Stops future timers and aborts pending checks.

### `dashboard/frontend/src/polling.test.js`

Node tests for polling behavior, without requiring a browser or AWS.

- **[Async helpers](../dashboard/frontend/src/polling.test.js#L5):** Gives pending promises/timers time to settle and fails if the expected state never arrives.
- **[Failure isolation test](../dashboard/frontend/src/polling.test.js#L11):** Leaves one service hanging and another failed, and verifies healthy service checks still finish.
- **[Recovery test](../dashboard/frontend/src/polling.test.js#L28):** Makes readiness fail once, then proves the next automatic poll succeeds.
- **[Cleanup/overlap test](../dashboard/frontend/src/polling.test.js#L42):** Proves manual refresh does not duplicate pending checks and stop prevents later UI updates.

### `dashboard/frontend/vite.config.js`

Project support configuration.

- **[React compilation](../dashboard/frontend/vite.config.js#L5):** Enables React handling during Vite development/build.
- **[Development-only proxy](../dashboard/frontend/vite.config.js#L8):** Forwards /api to a locally configured gateway during Vite development. Production traffic uses nginx in EKS instead.

### `data/raw/forecasting_data.csv`

Raw training data.

- **Header:** `timestamp, value` names the data fields.
- **Rows:** supply examples for the matching training script; the saved model learns patterns from these rows.
- **Deployment:** the dashboard submits new input; these rows are not used as static displayed prediction results.

### `data/raw/fraud_assessment_dataset.csv`

Raw training data.

- **Header:** `transaction_id, amount, transaction_count, account_age_days, risk_score, fraud` names the data fields.
- **Rows:** supply examples for the matching training script; the saved model learns patterns from these rows.
- **Deployment:** the dashboard submits new input; these rows are not used as static displayed prediction results.

### `data/raw/recommendations_data.csv`

Raw training data and the deployed item catalog.

- **Header:** `user_id, category, item_id, rating, clicked` names the data fields.
- **Rows:** supply examples for the matching training script; the saved model learns patterns from these rows.
- **Deployment:** the dashboard submits new input; these rows are not used as static displayed prediction results.

### `docs/architecture/platform-architecture.md`

Project documentation, not running application code.

- **Reading notes:** Explains how the deployed platform components fit together.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `docs/aws-iam/forecasting-invoke-policy.json`

JSON configuration or recorded verification evidence.

- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.

### `docs/aws-iam/forecasting-invoke-trust.json`

JSON configuration or recorded verification evidence.

- **Principal / Action:** identifies who may assume the role and the allowed assume-role operations.
- **Condition:** limits that trust to the project account or the intended EKS cluster/namespace/ServiceAccount.

### `docs/aws-iam/fraud-invoke-policy.json`

JSON configuration or recorded verification evidence.

- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.

### `docs/aws-iam/fraud-invoke-trust.json`

JSON configuration or recorded verification evidence.

- **Principal / Action:** identifies who may assume the role and the allowed assume-role operations.
- **Condition:** limits that trust to the project account or the intended EKS cluster/namespace/ServiceAccount.

### `docs/aws-iam/recommendations-invoke-policy.json`

JSON configuration or recorded verification evidence.

- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.

### `docs/aws-iam/recommendations-invoke-trust.json`

JSON configuration or recorded verification evidence.

- **Principal / Action:** identifies who may assume the role and the allowed assume-role operations.
- **Condition:** limits that trust to the project account or the intended EKS cluster/namespace/ServiceAccount.

### `docs/aws-iam/sagemaker-execution-policy.json`

JSON configuration or recorded verification evidence.

- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.
- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.
- **Effect / Action:** lists permitted AWS operations.
- **Resource:** scopes those operations to this endpoint, image repository, or endpoint log group; registry authentication uses the required wildcard.

### `docs/aws-iam/sagemaker-execution-trust.json`

JSON configuration or recorded verification evidence.

- **Principal / Action:** identifies who may assume the role and the allowed assume-role operations.
- **Condition:** limits that trust to the project account or the intended EKS cluster/namespace/ServiceAccount.

### `docs/aws-resource-ownership.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Rows identify tracked AWS resources, their ARNs, and Owner/Project tags; this file is evidence, not resource-creation instructions.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/dashboard-api-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records API-supplied metadata and separate health/readiness results.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/dashboard-browser-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records real rendered metadata, repeated polling, browser-only outage isolation, live prediction during the simulation, and recovery.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/dashboard-operations.md`

Project documentation, not running application code.

- **Reading notes:** Explains API-backed metadata, independent polling, failure isolation, and dashboard verification.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `docs/dashboard-operations.png`

Visual asset or screenshot, not executable application code.

- **Purpose:** Shows the actual verified operations dashboard.
- **Format:** PNG contains pixels; SVG describes vector shapes.

### `docs/frontend-probe-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records that removing/restoring the frontend page changes readiness while process health stays up.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/kubernetes-deployment.md`

Project documentation, not running application code.

- **Reading notes:** Explains namespaces, budgets, probes, identity, validation, rollback, and how to access the deployed frontend.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `docs/kubernetes-migration-rollback.yaml`

Saved Kubernetes resources for restoring the previous single-namespace workload copies.

- **[Deployment: forecasting-service](../docs/kubernetes-migration-rollback.yaml#L3):** Defines this Deployment in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../docs/kubernetes-migration-rollback.yaml#L14):** Keeps 2 pod(s) available for this workload.
- **[Pod selection](../docs/kubernetes-migration-rollback.yaml#L17):** Matches this Deployment to its own pod labels.
- **[Pod template](../docs/kubernetes-migration-rollback.yaml#L26):** Defines what each new pod will run.
- **[Container image](../docs/kubernetes-migration-rollback.yaml#L40):** Chooses the built release from the existing ECR repository.
- **[Application port](../docs/kubernetes-migration-rollback.yaml#L55):** Documents the port served inside the container.
- **[Configuration](../docs/kubernetes-migration-rollback.yaml#L36):** Loads the matching ConfigMap into environment variables.
- **[Liveness check](../docs/kubernetes-migration-rollback.yaml#L43):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../docs/kubernetes-migration-rollback.yaml#L59):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../docs/kubernetes-migration-rollback.yaml#L70):** Requests reserve scheduling capacity; limits cap use.
- **[AWS identity](../docs/kubernetes-migration-rollback.yaml#L85):** Selects the ServiceAccount linked to a scoped Pod Identity role.

- **[Deployment: recommendations-service](../docs/kubernetes-migration-rollback.yaml#L90):** Defines this Deployment in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L90):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L94):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../docs/kubernetes-migration-rollback.yaml#L101):** Keeps 2 pod(s) available for this workload.
- **[Pod selection](../docs/kubernetes-migration-rollback.yaml#L104):** Matches this Deployment to its own pod labels.
- **[Pod template](../docs/kubernetes-migration-rollback.yaml#L113):** Defines what each new pod will run.
- **[Container image](../docs/kubernetes-migration-rollback.yaml#L127):** Chooses the built release from the existing ECR repository.
- **[Application port](../docs/kubernetes-migration-rollback.yaml#L142):** Documents the port served inside the container.
- **[Configuration](../docs/kubernetes-migration-rollback.yaml#L123):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../docs/kubernetes-migration-rollback.yaml#L165):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../docs/kubernetes-migration-rollback.yaml#L130):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../docs/kubernetes-migration-rollback.yaml#L146):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../docs/kubernetes-migration-rollback.yaml#L157):** Requests reserve scheduling capacity; limits cap use.
- **[AWS identity](../docs/kubernetes-migration-rollback.yaml#L182):** Selects the ServiceAccount linked to a scoped Pod Identity role.

- **[Deployment: gateway-service](../docs/kubernetes-migration-rollback.yaml#L187):** Defines this Deployment in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L187):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L191):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../docs/kubernetes-migration-rollback.yaml#L198):** Keeps 1 pod(s) available for this workload.
- **[Pod selection](../docs/kubernetes-migration-rollback.yaml#L201):** Matches this Deployment to its own pod labels.
- **[Pod template](../docs/kubernetes-migration-rollback.yaml#L210):** Defines what each new pod will run.
- **[Container image](../docs/kubernetes-migration-rollback.yaml#L222):** Chooses the built release from the existing ECR repository.
- **[Application port](../docs/kubernetes-migration-rollback.yaml#L236):** Documents the port served inside the container.
- **[Configuration](../docs/kubernetes-migration-rollback.yaml#L218):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../docs/kubernetes-migration-rollback.yaml#L258):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../docs/kubernetes-migration-rollback.yaml#L225):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../docs/kubernetes-migration-rollback.yaml#L240):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../docs/kubernetes-migration-rollback.yaml#L250):** Requests reserve scheduling capacity; limits cap use.

- **[Deployment: frontend-service](../docs/kubernetes-migration-rollback.yaml#L277):** Defines this Deployment in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L277):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L281):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../docs/kubernetes-migration-rollback.yaml#L288):** Keeps 1 pod(s) available for this workload.
- **[Pod selection](../docs/kubernetes-migration-rollback.yaml#L291):** Matches this Deployment to its own pod labels.
- **[Pod template](../docs/kubernetes-migration-rollback.yaml#L300):** Defines what each new pod will run.
- **[Container image](../docs/kubernetes-migration-rollback.yaml#L308):** Chooses the built release from the existing ECR repository.
- **[Application port](../docs/kubernetes-migration-rollback.yaml#L322):** Documents the port served inside the container.
- **[Startup check](../docs/kubernetes-migration-rollback.yaml#L344):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../docs/kubernetes-migration-rollback.yaml#L311):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../docs/kubernetes-migration-rollback.yaml#L326):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../docs/kubernetes-migration-rollback.yaml#L336):** Requests reserve scheduling capacity; limits cap use.

- **[Service: forecasting-service](../docs/kubernetes-migration-rollback.yaml#L363):** Defines this Service in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L363):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L367):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../docs/kubernetes-migration-rollback.yaml#L382):** Uses an internal stable ClusterIP address.
- **[Matching pods](../docs/kubernetes-migration-rollback.yaml#L378):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../docs/kubernetes-migration-rollback.yaml#L373):** Maps the Service port to the target container port.

- **[Service: recommendations-service](../docs/kubernetes-migration-rollback.yaml#L386):** Defines this Service in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L386):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L390):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../docs/kubernetes-migration-rollback.yaml#L405):** Uses an internal stable ClusterIP address.
- **[Matching pods](../docs/kubernetes-migration-rollback.yaml#L401):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../docs/kubernetes-migration-rollback.yaml#L396):** Maps the Service port to the target container port.

- **[Service: gateway-service](../docs/kubernetes-migration-rollback.yaml#L409):** Defines this Service in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L409):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L413):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../docs/kubernetes-migration-rollback.yaml#L428):** Uses an internal stable ClusterIP address.
- **[Matching pods](../docs/kubernetes-migration-rollback.yaml#L424):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../docs/kubernetes-migration-rollback.yaml#L419):** Maps the Service port to the target container port.

- **[Service: frontend-service](../docs/kubernetes-migration-rollback.yaml#L432):** Defines this Service in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L432):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L436):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../docs/kubernetes-migration-rollback.yaml#L451):** Uses an internal stable ClusterIP address.
- **[Matching pods](../docs/kubernetes-migration-rollback.yaml#L447):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../docs/kubernetes-migration-rollback.yaml#L442):** Maps the Service port to the target container port.

- **[ConfigMap: forecasting-config](../docs/kubernetes-migration-rollback.yaml#L455):** Defines this ConfigMap in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L455):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L470):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[AWS_REGION](../docs/kubernetes-migration-rollback.yaml#L458):** Chooses the AWS region.
- **[FORECASTING_SAGEMAKER_ENDPOINT](../docs/kubernetes-migration-rollback.yaml#L460):** Names this service’s SageMaker endpoint.
- **[MODEL_PATH](../docs/kubernetes-migration-rollback.yaml#L462):** Supplies a non-secret application setting.
- **[MODEL_PROVIDER](../docs/kubernetes-migration-rollback.yaml#L464):** Selects SageMaker invocation for the deployed adapter.
- **[SERVICE_NAME](../docs/kubernetes-migration-rollback.yaml#L466):** Supplies a non-secret application setting.
- **[ConfigMap: recommendations-config](../docs/kubernetes-migration-rollback.yaml#L476):** Defines this ConfigMap in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L476):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L493):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[AWS_REGION](../docs/kubernetes-migration-rollback.yaml#L479):** Chooses the AWS region.
- **[MODEL_PATH](../docs/kubernetes-migration-rollback.yaml#L481):** Supplies a non-secret application setting.
- **[MODEL_PROVIDER](../docs/kubernetes-migration-rollback.yaml#L483):** Selects SageMaker invocation for the deployed adapter.
- **[RECOMMENDATIONS_CATALOG_PATH](../docs/kubernetes-migration-rollback.yaml#L485):** Supplies a non-secret application setting.
- **[RECOMMENDATIONS_SAGEMAKER_ENDPOINT](../docs/kubernetes-migration-rollback.yaml#L487):** Names this service’s SageMaker endpoint.
- **[SERVICE_NAME](../docs/kubernetes-migration-rollback.yaml#L489):** Supplies a non-secret application setting.
- **[ConfigMap: gateway-config](../docs/kubernetes-migration-rollback.yaml#L499):** Defines this ConfigMap in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L499):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L510):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[FORECASTING_SERVICE_URL](../docs/kubernetes-migration-rollback.yaml#L502):** Points the gateway to the correct service across namespaces.
- **[FRAUD_SERVICE_URL](../docs/kubernetes-migration-rollback.yaml#L504):** Points the gateway to the correct service across namespaces.
- **[RECOMMENDATIONS_SERVICE_URL](../docs/kubernetes-migration-rollback.yaml#L506):** Points the gateway to the correct service across namespaces.
- **[ServiceAccount: forecasting-sagemaker](../docs/kubernetes-migration-rollback.yaml#L516):** Defines this ServiceAccount in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L516):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L520):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Identity name:** EKS Pod Identity associates this ServiceAccount and namespace with the service-specific AWS invocation role. No static AWS key is stored here.
- **[ServiceAccount: recommendations-sagemaker](../docs/kubernetes-migration-rollback.yaml#L528):** Defines this ServiceAccount in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L528):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L532):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Identity name:** EKS Pod Identity associates this ServiceAccount and namespace with the service-specific AWS invocation role. No static AWS key is stored here.
- **[Ingress: assessment4-ingress](../docs/kubernetes-migration-rollback.yaml#L540):** Defines this Ingress in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L540):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L544):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Annotations / ingressClassName:** tell an nginx ingress controller how to interpret paths, rewriting, and timeouts.
- **rules / paths / backend:** match API or page traffic and send it to the correct Service.
- **Deployment distinction:** these rules need an installed ingress controller to provide external routing; the verified demo uses a tunnel to the deployed frontend.
- **[Ingress: assessment4-frontend](../docs/kubernetes-migration-rollback.yaml#L565):** Defines this Ingress in `fraud-team`.
- **[apiVersion / kind](../docs/kubernetes-migration-rollback.yaml#L565):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../docs/kubernetes-migration-rollback.yaml#L569):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Annotations / ingressClassName:** tell an nginx ingress controller how to interpret paths, rewriting, and timeouts.
- **rules / paths / backend:** match API or page traffic and send it to the correct Service.
- **Deployment distinction:** these rules need an installed ingress controller to provide external routing; the verified demo uses a tunnel to the deployed frontend.

### `docs/kubernetes-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records verification time, replicas, ready endpoint addresses, restart counts, probe definitions, admission-policy checks, test count, and release tag.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/live-integration-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records frontend assets, probe checks, request IDs, and actual model results through the deployed path.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/live-validation-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records malformed requests and their safe 422 responses.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/pod-identity-verification.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Records each checked pod’s scoped assumed-role identity and successful endpoint invocation.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `docs/sagemaker-deployment.md`

Project documentation, not running application code.

- **Reading notes:** Explains packaging existing artifacts, SageMaker hosting, identity, deployment commands, and recorded verification.
- **Code fences:** show example commands; they do not execute merely because the document is opened.

### `docs/sagemaker-resource-plan.json`

JSON configuration or recorded verification evidence.

- **Recorded fields:** Describes the intended account/region, endpoints, serverless capacity, identity roles/namespaces, and scoped policies. A plan is not proof that resources were created.
- **Interpretation:** verification files describe the checks at their recorded time; they are not a continuous health monitor.

### `k8s/configmaps/forecasting-config.yaml`

Kubernetes resource definition.

- **[ConfigMap: forecasting-config](../k8s/configmaps/forecasting-config.yaml#L3):** Defines this ConfigMap in `forecasting-team`.
- **[apiVersion / kind](../k8s/configmaps/forecasting-config.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/configmaps/forecasting-config.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[SERVICE_NAME](../k8s/configmaps/forecasting-config.yaml#L15):** Supplies a non-secret application setting.
- **[MODEL_PROVIDER](../k8s/configmaps/forecasting-config.yaml#L17):** Selects SageMaker invocation for the deployed adapter.
- **[MODEL_PATH](../k8s/configmaps/forecasting-config.yaml#L19):** Supplies a non-secret application setting.
- **[AWS_REGION](../k8s/configmaps/forecasting-config.yaml#L21):** Chooses the AWS region.
- **[FORECASTING_SAGEMAKER_ENDPOINT](../k8s/configmaps/forecasting-config.yaml#L23):** Names this service’s SageMaker endpoint.
- **[TEAM_NAME](../k8s/configmaps/forecasting-config.yaml#L25):** Identifies the owning team in logs and dashboard metadata.
- **[MODEL_NAME](../k8s/configmaps/forecasting-config.yaml#L27):** Identifies the configured model for the dashboard.
- **[MODEL_VERSION](../k8s/configmaps/forecasting-config.yaml#L29):** Identifies the model release.
- **[SERVICE_VERSION](../k8s/configmaps/forecasting-config.yaml#L31):** Identifies the application release; rendering overwrites it with the requested image tag.

### `k8s/configmaps/fraud-config.yaml`

Kubernetes resource definition.

- **[ConfigMap: fraud-config](../k8s/configmaps/fraud-config.yaml#L3):** Defines this ConfigMap in `fraud-team`.
- **[apiVersion / kind](../k8s/configmaps/fraud-config.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/configmaps/fraud-config.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[SERVICE_NAME](../k8s/configmaps/fraud-config.yaml#L15):** Supplies a non-secret application setting.
- **[MODEL_PROVIDER](../k8s/configmaps/fraud-config.yaml#L17):** Selects SageMaker invocation for the deployed adapter.
- **[MODEL_PATH](../k8s/configmaps/fraud-config.yaml#L19):** Supplies a non-secret application setting.
- **[AWS_REGION](../k8s/configmaps/fraud-config.yaml#L21):** Chooses the AWS region.
- **[FRAUD_SAGEMAKER_ENDPOINT](../k8s/configmaps/fraud-config.yaml#L23):** Names this service’s SageMaker endpoint.
- **[TEAM_NAME](../k8s/configmaps/fraud-config.yaml#L25):** Identifies the owning team in logs and dashboard metadata.
- **[MODEL_NAME](../k8s/configmaps/fraud-config.yaml#L27):** Identifies the configured model for the dashboard.
- **[MODEL_VERSION](../k8s/configmaps/fraud-config.yaml#L29):** Identifies the model release.
- **[SERVICE_VERSION](../k8s/configmaps/fraud-config.yaml#L31):** Identifies the application release; rendering overwrites it with the requested image tag.

### `k8s/configmaps/gateway-config.yaml`

Kubernetes resource definition.

- **[ConfigMap: gateway-config](../k8s/configmaps/gateway-config.yaml#L3):** Defines this ConfigMap in `platform-team`.
- **[apiVersion / kind](../k8s/configmaps/gateway-config.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/configmaps/gateway-config.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[FRAUD_SERVICE_URL](../k8s/configmaps/gateway-config.yaml#L15):** Points the gateway to the correct service across namespaces.
- **[FORECASTING_SERVICE_URL](../k8s/configmaps/gateway-config.yaml#L17):** Points the gateway to the correct service across namespaces.
- **[RECOMMENDATIONS_SERVICE_URL](../k8s/configmaps/gateway-config.yaml#L19):** Points the gateway to the correct service across namespaces.
- **[TEAM_NAME](../k8s/configmaps/gateway-config.yaml#L21):** Identifies the owning team in logs and dashboard metadata.
- **[SERVICE_VERSION](../k8s/configmaps/gateway-config.yaml#L23):** Identifies the application release; rendering overwrites it with the requested image tag.

### `k8s/configmaps/recommendations-config.yaml`

Kubernetes resource definition.

- **[ConfigMap: recommendations-config](../k8s/configmaps/recommendations-config.yaml#L3):** Defines this ConfigMap in `recommendations-team`.
- **[apiVersion / kind](../k8s/configmaps/recommendations-config.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/configmaps/recommendations-config.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[SERVICE_NAME](../k8s/configmaps/recommendations-config.yaml#L15):** Supplies a non-secret application setting.
- **[MODEL_PROVIDER](../k8s/configmaps/recommendations-config.yaml#L17):** Selects SageMaker invocation for the deployed adapter.
- **[MODEL_PATH](../k8s/configmaps/recommendations-config.yaml#L19):** Supplies a non-secret application setting.
- **[AWS_REGION](../k8s/configmaps/recommendations-config.yaml#L21):** Chooses the AWS region.
- **[RECOMMENDATIONS_CATALOG_PATH](../k8s/configmaps/recommendations-config.yaml#L23):** Supplies a non-secret application setting.
- **[RECOMMENDATIONS_SAGEMAKER_ENDPOINT](../k8s/configmaps/recommendations-config.yaml#L25):** Names this service’s SageMaker endpoint.
- **[TEAM_NAME](../k8s/configmaps/recommendations-config.yaml#L27):** Identifies the owning team in logs and dashboard metadata.
- **[MODEL_NAME](../k8s/configmaps/recommendations-config.yaml#L29):** Identifies the configured model for the dashboard.
- **[MODEL_VERSION](../k8s/configmaps/recommendations-config.yaml#L31):** Identifies the model release.
- **[SERVICE_VERSION](../k8s/configmaps/recommendations-config.yaml#L33):** Identifies the application release; rendering overwrites it with the requested image tag.

### `k8s/deployments/forecasting.yaml`

Kubernetes resource definition.

- **[Deployment: forecasting-service](../k8s/deployments/forecasting.yaml#L3):** Defines this Deployment in `forecasting-team`.
- **[apiVersion / kind](../k8s/deployments/forecasting.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/deployments/forecasting.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../k8s/deployments/forecasting.yaml#L15):** Keeps 2 pod(s) available for this workload.
- **[Pod selection](../k8s/deployments/forecasting.yaml#L17):** Matches this Deployment to its own pod labels.
- **[Pod template](../k8s/deployments/forecasting.yaml#L21):** Defines what each new pod will run.
- **[Container image](../k8s/deployments/forecasting.yaml#L31):** Chooses the built release from the existing ECR repository.
- **[Application port](../k8s/deployments/forecasting.yaml#L34):** Documents the port served inside the container.
- **[Configuration](../k8s/deployments/forecasting.yaml#L37):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../k8s/deployments/forecasting.yaml#L66):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../k8s/deployments/forecasting.yaml#L49):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../k8s/deployments/forecasting.yaml#L41):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../k8s/deployments/forecasting.yaml#L57):** Requests reserve scheduling capacity; limits cap use.
- **[AWS identity](../k8s/deployments/forecasting.yaml#L74):** Selects the ServiceAccount linked to a scoped Pod Identity role.


### `k8s/deployments/fraud.yaml`

Kubernetes resource definition.

- **[Deployment: fraud-service](../k8s/deployments/fraud.yaml#L3):** Defines this Deployment in `fraud-team`.
- **[apiVersion / kind](../k8s/deployments/fraud.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/deployments/fraud.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../k8s/deployments/fraud.yaml#L16):** Keeps 1 pod(s) available for this workload.
- **[Pod selection](../k8s/deployments/fraud.yaml#L18):** Matches this Deployment to its own pod labels.
- **[Pod template](../k8s/deployments/fraud.yaml#L22):** Defines what each new pod will run.
- **[Container image](../k8s/deployments/fraud.yaml#L32):** Chooses the built release from the existing ECR repository.
- **[Application port](../k8s/deployments/fraud.yaml#L35):** Documents the port served inside the container.
- **[Configuration](../k8s/deployments/fraud.yaml#L38):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../k8s/deployments/fraud.yaml#L42):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../k8s/deployments/fraud.yaml#L59):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../k8s/deployments/fraud.yaml#L50):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../k8s/deployments/fraud.yaml#L68):** Requests reserve scheduling capacity; limits cap use.
- **[AWS identity](../k8s/deployments/fraud.yaml#L77):** Selects the ServiceAccount linked to a scoped Pod Identity role.


### `k8s/deployments/frontend.yaml`

Kubernetes resource definition.

- **[Deployment: frontend-service](../k8s/deployments/frontend.yaml#L3):** Defines this Deployment in `platform-team`.
- **[apiVersion / kind](../k8s/deployments/frontend.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/deployments/frontend.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../k8s/deployments/frontend.yaml#L15):** Keeps 1 pod(s) available for this workload.
- **[Pod selection](../k8s/deployments/frontend.yaml#L17):** Matches this Deployment to its own pod labels.
- **[Pod template](../k8s/deployments/frontend.yaml#L21):** Defines what each new pod will run.
- **[Container image](../k8s/deployments/frontend.yaml#L31):** Chooses the built release from the existing ECR repository.
- **[Application port](../k8s/deployments/frontend.yaml#L33):** Documents the port served inside the container.
- **[Startup check](../k8s/deployments/frontend.yaml#L36):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../k8s/deployments/frontend.yaml#L44):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../k8s/deployments/frontend.yaml#L50):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../k8s/deployments/frontend.yaml#L56):** Requests reserve scheduling capacity; limits cap use.


### `k8s/deployments/gateway.yaml`

Kubernetes resource definition.

- **[Deployment: gateway-service](../k8s/deployments/gateway.yaml#L3):** Defines this Deployment in `platform-team`.
- **[apiVersion / kind](../k8s/deployments/gateway.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/deployments/gateway.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../k8s/deployments/gateway.yaml#L15):** Keeps 1 pod(s) available for this workload.
- **[Pod selection](../k8s/deployments/gateway.yaml#L17):** Matches this Deployment to its own pod labels.
- **[Pod template](../k8s/deployments/gateway.yaml#L21):** Defines what each new pod will run.
- **[Container image](../k8s/deployments/gateway.yaml#L31):** Chooses the built release from the existing ECR repository.
- **[Application port](../k8s/deployments/gateway.yaml#L33):** Documents the port served inside the container.
- **[Configuration](../k8s/deployments/gateway.yaml#L36):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../k8s/deployments/gateway.yaml#L40):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../k8s/deployments/gateway.yaml#L48):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../k8s/deployments/gateway.yaml#L54):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../k8s/deployments/gateway.yaml#L61):** Requests reserve scheduling capacity; limits cap use.


### `k8s/deployments/recommendations.yaml`

Kubernetes resource definition.

- **[Deployment: recommendations-service](../k8s/deployments/recommendations.yaml#L3):** Defines this Deployment in `recommendations-team`.
- **[apiVersion / kind](../k8s/deployments/recommendations.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/deployments/recommendations.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Replica count](../k8s/deployments/recommendations.yaml#L15):** Keeps 2 pod(s) available for this workload.
- **[Pod selection](../k8s/deployments/recommendations.yaml#L17):** Matches this Deployment to its own pod labels.
- **[Pod template](../k8s/deployments/recommendations.yaml#L21):** Defines what each new pod will run.
- **[Container image](../k8s/deployments/recommendations.yaml#L31):** Chooses the built release from the existing ECR repository.
- **[Application port](../k8s/deployments/recommendations.yaml#L34):** Documents the port served inside the container.
- **[Configuration](../k8s/deployments/recommendations.yaml#L37):** Loads the matching ConfigMap into environment variables.
- **[Startup check](../k8s/deployments/recommendations.yaml#L57):** Allows initialization before regular health checks can cause restarts.
- **[Liveness check](../k8s/deployments/recommendations.yaml#L49):** Calls `/health` and restarts a stuck process after repeated failure.
- **[Readiness check](../k8s/deployments/recommendations.yaml#L41):** Calls `/ready`; unready pods stop receiving Service traffic.
- **[CPU/memory](../k8s/deployments/recommendations.yaml#L65):** Requests reserve scheduling capacity; limits cap use.
- **[AWS identity](../k8s/deployments/recommendations.yaml#L74):** Selects the ServiceAccount linked to a scoped Pod Identity role.


### `k8s/exposure/frontend-public.yaml`

Kubernetes resource definition.

- **[Service: frontend-public](../k8s/exposure/frontend-public.yaml#L3):** Defines this Service in `platform-team`.
- **[apiVersion / kind](../k8s/exposure/frontend-public.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/exposure/frontend-public.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../k8s/exposure/frontend-public.yaml#L17):** Requests a public AWS load balancer if explicitly applied; it can add AWS cost.
- **[Matching pods](../k8s/exposure/frontend-public.yaml#L19):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/exposure/frontend-public.yaml#L22):** Maps the Service port to the target container port.


### `k8s/ingress/ingress.yaml`

Kubernetes resource definition.

- **[Ingress: assessment4-ingress](../k8s/ingress/ingress.yaml#L3):** Defines this Ingress in `platform-team`.
- **[apiVersion / kind](../k8s/ingress/ingress.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/ingress/ingress.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Annotations / ingressClassName:** tell an nginx ingress controller how to interpret paths, rewriting, and timeouts.
- **rules / paths / backend:** match API or page traffic and send it to the correct Service.
- **Deployment distinction:** these rules need an installed ingress controller to provide external routing; the verified demo uses a tunnel to the deployed frontend.
- **[Ingress: assessment4-frontend](../k8s/ingress/ingress.yaml#L33):** Defines this Ingress in `platform-team`.
- **[apiVersion / kind](../k8s/ingress/ingress.yaml#L33):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/ingress/ingress.yaml#L37):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Annotations / ingressClassName:** tell an nginx ingress controller how to interpret paths, rewriting, and timeouts.
- **rules / paths / backend:** match API or page traffic and send it to the correct Service.
- **Deployment distinction:** these rules need an installed ingress controller to provide external routing; the verified demo uses a tunnel to the deployed frontend.

### `k8s/namespaces/forecasting-team.yaml`

Kubernetes resource definition.

- **[Namespace: forecasting-team](../k8s/namespaces/forecasting-team.yaml#L3):** Defines this Namespace in `forecasting-team`.
- **[apiVersion / kind](../k8s/namespaces/forecasting-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/namespaces/forecasting-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Namespace boundary:** separates this team/platform workload’s names and resource budgets; it is not by itself a network firewall.

### `k8s/namespaces/fraud-team.yaml`

Kubernetes resource definition.

- **[Namespace: fraud-team](../k8s/namespaces/fraud-team.yaml#L3):** Defines this Namespace in `fraud-team`.
- **[apiVersion / kind](../k8s/namespaces/fraud-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/namespaces/fraud-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Namespace boundary:** separates this team/platform workload’s names and resource budgets; it is not by itself a network firewall.

### `k8s/namespaces/platform-team.yaml`

Kubernetes resource definition.

- **[Namespace: platform-team](../k8s/namespaces/platform-team.yaml#L3):** Defines this Namespace in `platform-team`.
- **[apiVersion / kind](../k8s/namespaces/platform-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/namespaces/platform-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Namespace boundary:** separates this team/platform workload’s names and resource budgets; it is not by itself a network firewall.

### `k8s/namespaces/recommendations-team.yaml`

Kubernetes resource definition.

- **[Namespace: recommendations-team](../k8s/namespaces/recommendations-team.yaml#L3):** Defines this Namespace in `recommendations-team`.
- **[apiVersion / kind](../k8s/namespaces/recommendations-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/namespaces/recommendations-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Namespace boundary:** separates this team/platform workload’s names and resource budgets; it is not by itself a network firewall.

### `k8s/observability/hpa.yaml`

Kubernetes resource definition.

- **[HorizontalPodAutoscaler: fraud-service-hpa](../k8s/observability/hpa.yaml#L3):** Defines this HorizontalPodAutoscaler in `fraud-team`.
- **[apiVersion / kind](../k8s/observability/hpa.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/observability/hpa.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **scaleTargetRef:** names the fraud Deployment to resize.
- **minReplicas / maxReplicas:** bounds replicas between one and three.
- **metrics:** targets 70 percent CPU utilization relative to requests.
- **Application status:** this optional manifest is outside the folders applied by the current render/deploy script; its presence alone does not mean autoscaling is active.

### `k8s/policies/forecasting-team.yaml`

Kubernetes resource definition.

- **[ResourceQuota: workload-budget](../k8s/policies/forecasting-team.yaml#L3):** Defines this ResourceQuota in `forecasting-team`.
- **[apiVersion / kind](../k8s/policies/forecasting-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/forecasting-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.hard:** caps total requested CPU/memory, allowed CPU/memory limits, and pod count for this namespace. These ceilings do not create or reserve AWS nodes.
- **[LimitRange: container-defaults](../k8s/policies/forecasting-team.yaml#L24):** Defines this LimitRange in `forecasting-team`.
- **[apiVersion / kind](../k8s/policies/forecasting-team.yaml#L24):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/forecasting-team.yaml#L28):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.limits:** sets per-container minimums, maximums, and default requests/limits when a container omits them.

### `k8s/policies/fraud-team.yaml`

Kubernetes resource definition.

- **[ResourceQuota: workload-budget](../k8s/policies/fraud-team.yaml#L3):** Defines this ResourceQuota in `fraud-team`.
- **[apiVersion / kind](../k8s/policies/fraud-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/fraud-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.hard:** caps total requested CPU/memory, allowed CPU/memory limits, and pod count for this namespace. These ceilings do not create or reserve AWS nodes.
- **[LimitRange: container-defaults](../k8s/policies/fraud-team.yaml#L24):** Defines this LimitRange in `fraud-team`.
- **[apiVersion / kind](../k8s/policies/fraud-team.yaml#L24):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/fraud-team.yaml#L28):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.limits:** sets per-container minimums, maximums, and default requests/limits when a container omits them.

### `k8s/policies/platform-team.yaml`

Kubernetes resource definition.

- **[ResourceQuota: workload-budget](../k8s/policies/platform-team.yaml#L3):** Defines this ResourceQuota in `platform-team`.
- **[apiVersion / kind](../k8s/policies/platform-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/platform-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.hard:** caps total requested CPU/memory, allowed CPU/memory limits, and pod count for this namespace. These ceilings do not create or reserve AWS nodes.
- **[LimitRange: container-defaults](../k8s/policies/platform-team.yaml#L24):** Defines this LimitRange in `platform-team`.
- **[apiVersion / kind](../k8s/policies/platform-team.yaml#L24):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/platform-team.yaml#L28):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.limits:** sets per-container minimums, maximums, and default requests/limits when a container omits them.

### `k8s/policies/recommendations-team.yaml`

Kubernetes resource definition.

- **[ResourceQuota: workload-budget](../k8s/policies/recommendations-team.yaml#L3):** Defines this ResourceQuota in `recommendations-team`.
- **[apiVersion / kind](../k8s/policies/recommendations-team.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/recommendations-team.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.hard:** caps total requested CPU/memory, allowed CPU/memory limits, and pod count for this namespace. These ceilings do not create or reserve AWS nodes.
- **[LimitRange: container-defaults](../k8s/policies/recommendations-team.yaml#L24):** Defines this LimitRange in `recommendations-team`.
- **[apiVersion / kind](../k8s/policies/recommendations-team.yaml#L24):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/policies/recommendations-team.yaml#L28):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **spec.limits:** sets per-container minimums, maximums, and default requests/limits when a container omits them.

### `k8s/secrets/fraud-service-secret.yaml`

Kubernetes resource definition.

- **[Secret: fraud-service-secret](../k8s/secrets/fraud-service-secret.yaml#L3):** Defines this Secret in `fraud-team`.
- **[apiVersion / kind](../k8s/secrets/fraud-service-secret.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/secrets/fraud-service-secret.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **type / stringData:** defines placeholder API-key/database-password entries, not real credentials.
- **Application status:** this legacy example is not applied by the current deployment script and is not used for SageMaker access. Its demo-only comments do not describe the current integrated platform.

### `k8s/serviceaccounts/forecasting.yaml`

Kubernetes resource definition.

- **[ServiceAccount: forecasting-sagemaker](../k8s/serviceaccounts/forecasting.yaml#L3):** Defines this ServiceAccount in `forecasting-team`.
- **[apiVersion / kind](../k8s/serviceaccounts/forecasting.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/serviceaccounts/forecasting.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Identity name:** EKS Pod Identity associates this ServiceAccount and namespace with the service-specific AWS invocation role. No static AWS key is stored here.

### `k8s/serviceaccounts/fraud.yaml`

Kubernetes resource definition.

- **[ServiceAccount: fraud-sagemaker](../k8s/serviceaccounts/fraud.yaml#L3):** Defines this ServiceAccount in `fraud-team`.
- **[apiVersion / kind](../k8s/serviceaccounts/fraud.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/serviceaccounts/fraud.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Identity name:** EKS Pod Identity associates this ServiceAccount and namespace with the service-specific AWS invocation role. No static AWS key is stored here.

### `k8s/serviceaccounts/recommendations.yaml`

Kubernetes resource definition.

- **[ServiceAccount: recommendations-sagemaker](../k8s/serviceaccounts/recommendations.yaml#L3):** Defines this ServiceAccount in `recommendations-team`.
- **[apiVersion / kind](../k8s/serviceaccounts/recommendations.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/serviceaccounts/recommendations.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **Identity name:** EKS Pod Identity associates this ServiceAccount and namespace with the service-specific AWS invocation role. No static AWS key is stored here.

### `k8s/services/forecasting.yaml`

Kubernetes resource definition.

- **[Service: forecasting-service](../k8s/services/forecasting.yaml#L3):** Defines this Service in `forecasting-team`.
- **[apiVersion / kind](../k8s/services/forecasting.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/services/forecasting.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../k8s/services/forecasting.yaml#L22):** Uses an internal stable ClusterIP address.
- **[Matching pods](../k8s/services/forecasting.yaml#L15):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/services/forecasting.yaml#L18):** Maps the Service port to the target container port.


### `k8s/services/fraud.yaml`

Kubernetes resource definition.

- **[Service: fraud-service](../k8s/services/fraud.yaml#L3):** Defines this Service in `fraud-team`.
- **[apiVersion / kind](../k8s/services/fraud.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/services/fraud.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../k8s/services/fraud.yaml#L23):** Uses an internal stable ClusterIP address.
- **[Matching pods](../k8s/services/fraud.yaml#L15):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/services/fraud.yaml#L18):** Maps the Service port to the target container port.


### `k8s/services/frontend.yaml`

Kubernetes resource definition.

- **[Service: frontend-service](../k8s/services/frontend.yaml#L3):** Defines this Service in `platform-team`.
- **[apiVersion / kind](../k8s/services/frontend.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/services/frontend.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Matching pods](../k8s/services/frontend.yaml#L15):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/services/frontend.yaml#L18):** Maps the Service port to the target container port.


### `k8s/services/gateway.yaml`

Kubernetes resource definition.

- **[Service: gateway-service](../k8s/services/gateway.yaml#L3):** Defines this Service in `platform-team`.
- **[apiVersion / kind](../k8s/services/gateway.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/services/gateway.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Matching pods](../k8s/services/gateway.yaml#L15):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/services/gateway.yaml#L18):** Maps the Service port to the target container port.


### `k8s/services/recommendations.yaml`

Kubernetes resource definition.

- **[Service: recommendations-service](../k8s/services/recommendations.yaml#L3):** Defines this Service in `recommendations-team`.
- **[apiVersion / kind](../k8s/services/recommendations.yaml#L3):** Tells Kubernetes which resource type and schema to use.
- **[metadata](../k8s/services/recommendations.yaml#L7):** Supplies the name, namespace, and labels used to identify the workload and owner.
- **[Service type](../k8s/services/recommendations.yaml#L23):** Uses an internal stable ClusterIP address.
- **[Matching pods](../k8s/services/recommendations.yaml#L15):** Sends traffic only to pods matching this application’s labels.
- **[Port mapping](../k8s/services/recommendations.yaml#L18):** Maps the Service port to the target container port.


### `ml/models/forecasting_model.joblib`

Saved trained model artifact, not source code.

- **Serialized object:** stores learned random-forest parameters and model structure.
- **Loading:** joblib restores the object for actual inference inside SageMaker or offline tests.
- **Presentation line:** “I reuse this trained artifact for hosting; deployment does not require a new training job.”

### `ml/models/fraud_model.joblib`

Saved trained model artifact, not source code.

- **Serialized object:** stores learned random-forest parameters and model structure.
- **Loading:** joblib restores the object for actual inference inside SageMaker or offline tests.
- **Presentation line:** “I reuse this trained artifact for hosting; deployment does not require a new training job.”

### `ml/models/recommendations_model.joblib`

Saved trained model artifact, not source code.

- **Serialized object:** stores learned random-forest parameters and model structure.
- **Loading:** joblib restores the object for actual inference inside SageMaker or offline tests.
- **Presentation line:** “I reuse this trained artifact for hosting; deployment does not require a new training job.”

### `ml/serving/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../ml/serving/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../ml/serving/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../ml/serving/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../ml/serving/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../ml/serving/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../ml/serving/Dockerfile#L18):** Documents the port served by this image.
- **[Hosting mode](../ml/serving/Dockerfile#L16):** Defaults to local artifact execution inside the SageMaker container.
- **[Hosting startup](../ml/serving/Dockerfile#L20):** Launches the script that accepts SageMaker’s serve argument.

### `ml/serving/entrypoint.sh`

SageMaker container startup script.

- **[Argument check](../ml/serving/entrypoint.sh#L4):** Accepts SageMaker’s serve startup argument and rejects other commands.
- **[Run model server](../ml/serving/entrypoint.sh#L9):** Starts the hosting FastAPI app on port 8080 with one worker, replacing the shell process.

### `ml/serving/main.py`

Makes the existing artifact engine usable inside a real SageMaker hosting container.

- **[Imports and setup](../ml/serving/main.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[create_serving_app](../ml/serving/main.py#L21):** Selects the request/response contracts, forces real local model execution inside the hosting container, and adds SageMaker’s required routes.
- **[create_serving_app → ping](../ml/serving/main.py#L32):** Reports whether the hosted artifact is loaded, so SageMaker can check container readiness.
- **[Contract map](../ml/serving/main.py#L13):** Chooses the right request and response schema for each model.
- **[Hosting request route](../ml/serving/main.py#L28):** Reuses prediction handling under SageMaker’s `/invocations` path.
- **[Startup selection](../ml/serving/main.py#L39):** Chooses the model from SERVICE_NAME; the default is fraud.


### `ml/training/train_forecasting_model.py`

Trains and saves the forecasting model locally. This script is not a SageMaker training-job launcher.

- **[Imports](../ml/training/train_forecasting_model.py#L2):** Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
- **[Paths](../ml/training/train_forecasting_model.py#L11):** Locates the raw CSV and output model file relative to the project.
- **[Read data](../ml/training/train_forecasting_model.py#L18):** Loads the CSV into a table.
- **[Column checks](../ml/training/train_forecasting_model.py#L21):** Rejects input data that is missing required fields.
- **[Feature preparation](../ml/training/train_forecasting_model.py#L27):** Builds newest-first lag features from time-sorted history.
- **[Training/test split](../ml/training/train_forecasting_model.py#L38):** Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the class proportions.
- **[Model settings](../ml/training/train_forecasting_model.py#L43):** Creates a random forest: many decision trees voting on a class or averaging a numeric value.
- **[Training](../ml/training/train_forecasting_model.py#L49):** Learns patterns from the training portion.
- **[Evaluation](../ml/training/train_forecasting_model.py#L52):** Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
- **[Save artifact](../ml/training/train_forecasting_model.py#L57):** Creates the model folder if needed and saves the trained object with joblib.
- **[Entry point](../ml/training/train_forecasting_model.py#L63):** Runs training only when the file is executed directly.

### `ml/training/train_fraud_model.py`

Trains and saves the fraud model locally. This script is not a SageMaker training-job launcher.

- **[Imports](../ml/training/train_fraud_model.py#L2):** Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
- **[Paths](../ml/training/train_fraud_model.py#L11):** Locates the raw CSV and output model file relative to the project.
- **[Read data](../ml/training/train_fraud_model.py#L18):** Loads the CSV into a table.
- **[Column checks](../ml/training/train_fraud_model.py#L21):** Rejects input data that is missing required fields.
- **[Feature preparation](../ml/training/train_fraud_model.py#L27):** Uses amount, transaction count, and account age to predict the fraud label.
- **[Training/test split](../ml/training/train_fraud_model.py#L32):** Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the class proportions.
- **[Model settings](../ml/training/train_fraud_model.py#L37):** Creates a random forest: many decision trees voting on a class or averaging a numeric value.
- **[Training](../ml/training/train_fraud_model.py#L44):** Learns patterns from the training portion.
- **[Evaluation](../ml/training/train_fraud_model.py#L47):** Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
- **[Save artifact](../ml/training/train_fraud_model.py#L52):** Creates the model folder if needed and saves the trained object with joblib.
- **[Entry point](../ml/training/train_fraud_model.py#L58):** Runs training only when the file is executed directly.

### `ml/training/train_recommendations_model.py`

Trains and saves the recommendations model locally. This script is not a SageMaker training-job launcher.

- **[Imports](../ml/training/train_recommendations_model.py#L2):** Loads file-path helpers, data tools, a random-forest model, and evaluation functions.
- **[Paths](../ml/training/train_recommendations_model.py#L11):** Locates the raw CSV and output model file relative to the project.
- **[Read data](../ml/training/train_recommendations_model.py#L18):** Loads the CSV into a table.
- **[Column checks](../ml/training/train_recommendations_model.py#L21):** Rejects input data that is missing required fields.
- **[Feature preparation](../ml/training/train_recommendations_model.py#L27):** Converts category/item names to numeric codes and uses clicked as the target.
- **[Training/test split](../ml/training/train_recommendations_model.py#L34):** Holds out 20 percent for evaluation, with a repeatable random seed; classifiers keep the class proportions.
- **[Model settings](../ml/training/train_recommendations_model.py#L39):** Creates a random forest: many decision trees voting on a class or averaging a numeric value.
- **[Training](../ml/training/train_recommendations_model.py#L46):** Learns patterns from the training portion.
- **[Evaluation](../ml/training/train_recommendations_model.py#L49):** Predicts held-out examples and prints MAE for forecasting or accuracy for classification.
- **[Save artifact](../ml/training/train_recommendations_model.py#L54):** Creates the model folder if needed and saves the trained object with joblib.
- **[Entry point](../ml/training/train_recommendations_model.py#L60):** Runs training only when the file is executed directly.

### `pytest.ini`

Project support configuration.

- **addopts:** uses importlib mode to avoid confusion between repeated test_main.py filenames.
- **testpaths:** points pytest at apps and tests.

### `requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions. The scikit-learn pin matches the saved artifacts.

### `scripts/audit_aws_ownership.py`

Read-only audit of the project resources and their ownership tags.

- **[Imports and setup](../scripts/audit_aws_ownership.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[record](../scripts/audit_aws_ownership.py#L13):** Normalizes AWS tags into an ownership-inventory row.
- **[Hosting inventory](../scripts/audit_aws_ownership.py#L18):** Reads model/endpoint/configuration tags for each service.
- **[Role inventory](../scripts/audit_aws_ownership.py#L25):** Includes active roles and older roles retained for rollback.
- **[Cluster identity inventory](../scripts/audit_aws_ownership.py#L29):** Reads add-on and Pod Identity association tags.
- **[Ownership check](../scripts/audit_aws_ownership.py#L39):** Fails if any tracked resource is missing Anthony’s owner tag.


### `scripts/bootstrap.sh`

Read-only check of AWS identity and the existing EKS cluster.

- **[Settings](../scripts/bootstrap.sh#L4):** Selects the intended region and existing cluster.
- **[Caller check](../scripts/bootstrap.sh#L7):** Shows which AWS account/identity the CLI is using.
- **[Cluster check](../scripts/bootstrap.sh#L9):** Reads cluster name/status/version without making changes.

### `scripts/build.sh`

Builds and uploads the five application images into existing project repositories.

- **[Fail-fast settings](../scripts/build.sh#L3):** Stops on command errors, missing variables, or failed pipelines.
- **[Release settings](../scripts/build.sh#L7):** Reads the region/account and requires a selected image tag.
- **[Existing repositories](../scripts/build.sh#L14):** Checks the project repositories exist; it does not create them.
- **[Registry login](../scripts/build.sh#L17):** Authenticates Docker to ECR without printing a password.
- **[Build/upload](../scripts/build.sh#L30):** Builds Linux AMD64 images and uploads them. The hosting image disables OCI attestations for SageMaker compatibility.

### `scripts/build_sagemaker.sh`

Builds the special inference container SageMaker runs with the saved model artifacts.

- **[Fail-fast settings](../scripts/build_sagemaker.sh#L3):** Stops on command errors, missing variables, or failed pipelines.
- **[Release settings](../scripts/build_sagemaker.sh#L6):** Reads the region/account and requires a selected image tag.
- **[Existing repositories](../scripts/build_sagemaker.sh#L12):** Checks the project repositories exist; it does not create them.
- **[Registry login](../scripts/build_sagemaker.sh#L14):** Authenticates Docker to ECR without printing a password.
- **[Build/upload](../scripts/build_sagemaker.sh#L18):** Builds Linux AMD64 images and uploads them. The hosting image disables OCI attestations for SageMaker compatibility.

### `scripts/cleanup-ecr.sh`

Destructive legacy utility that deletes images from all three project ECR repositories. It is not part of the normal deployment flow.

- **[Repository list](../scripts/cleanup-ecr.sh#L8):** Targets the three owner-prefixed repositories.
- **[Image inventory](../scripts/cleanup-ecr.sh#L17):** Lists all image IDs and skips an empty repository.
- **[Deletion block](../scripts/cleanup-ecr.sh#L30):** Deletes the listed images, including potentially deployed releases; stops on deletion failure.

### `scripts/deploy.sh`

Validates and releases Kubernetes workloads in the existing cluster.

- **[Fail-fast settings](../scripts/deploy.sh#L3):** Stops if a required command fails.
- **[Release configuration](../scripts/deploy.sh#L6):** Selects release tag, AWS account/region, existing cluster, and Python executable.
- **[Test gate](../scripts/deploy.sh#L13):** Requires Python tests to pass before workload changes.
- **[Temporary YAML](../scripts/deploy.sh#L15):** Renders release manifests and cleans up its own temporary file on exit.
- **[Cluster connection](../scripts/deploy.sh#L19):** Points kubectl at the existing cluster.
- **[Client validation](../scripts/deploy.sh#L21):** Checks the manifests locally.
- **[Server admission](../scripts/deploy.sh#L25):** Validates on the live API server, creates namespace prerequisites, applies budgets, then checks admission again.
- **[Apply release](../scripts/deploy.sh#L32):** Applies the validated resources; this does not rebuild EKS or ECR.
- **[Rollout check](../scripts/deploy.sh#L34):** Waits for each Deployment in its correct namespace before declaring the release complete.

### `scripts/deploy_sagemaker.py`

Project-specific SageMaker and Pod Identity management. Its resource creation commands are separate from the offline plan.

- **[Imports and setup](../scripts/deploy_sagemaker.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[tags](../scripts/deploy_sagemaker.py#L33):** Labels created resources with the project and Anthony’s ownership.
- **[role_policy](../scripts/deploy_sagemaker.py#L38):** Builds endpoint-only invocation permissions for an adapter, or image-pull/log-writing permissions for hosting.
- **[hosting_trust](../scripts/deploy_sagemaker.py#L50):** Allows SageMaker in the intended AWS account to assume the execution role.
- **[workload_trust](../scripts/deploy_sagemaker.py#L57):** Allows EKS Pod Identity to assume a role only for the selected cluster, namespace, and service account.
- **[ensure_role](../scripts/deploy_sagemaker.py#L67):** Reuses an expected owned role or creates it, attaches its policy, and refuses an unexpected role/trust definition.
- **[endpoint_config](../scripts/deploy_sagemaker.py#L81):** Builds the 2 GB, maximum-concurrency-two serverless endpoint configuration.
- **[configure_identity](../scripts/deploy_sagemaker.py#L87):** Ensures the Pod Identity agent, dedicated invocation roles, and matching workload associations exist.
- **[identity](../scripts/deploy_sagemaker.py#L106):** Checks the AWS account before configuring workload identity, without creating SageMaker endpoints.
- **[provision](../scripts/deploy_sagemaker.py#L114):** Checks the account and immutable project image, then creates missing models/configurations/endpoints and refuses conflicting existing releases.
- **[status](../scripts/deploy_sagemaker.py#L149):** Reads each endpoint’s AWS deployment status and any failure reason.
- **[verify](../scripts/deploy_sagemaker.py#L159):** Invokes every real endpoint and validates meaningful fraud, forecast, and recommendation output.
- **[bind](../scripts/deploy_sagemaker.py#L180):** Verifies endpoints first, then writes environment configuration and Kubernetes ServiceAccounts for the adapters.
- **[main](../scripts/deploy_sagemaker.py#L202):** Selects the requested command: offline plan, identity setup, provision, status, verify, or bind.
- **[CLI entry point](../scripts/deploy_sagemaker.py#L219):** Runs the command parser when invoked as a script.


### `scripts/render_manifests.py`

Builds a complete Kubernetes manifest with the selected release images and service version.

- **[Imports and setup](../scripts/render_manifests.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[Release settings](../scripts/render_manifests.py#L9):** Requires an account and image tag and reads region/repository prefix settings.
- **[Manifest collection](../scripts/render_manifests.py#L14):** Reads namespaces, policies, ConfigMaps, ServiceAccounts, Deployments, Services, and ingress.
- **[Version injection](../scripts/render_manifests.py#L18):** Marks the configuration with the selected release tag.
- **[Image selection](../scripts/render_manifests.py#L22):** Uses each model’s ECR repository, sharing the fraud repository for gateway/frontend tags.
- **[Rendered output](../scripts/render_manifests.py#L28):** Prints YAML documents for validation and deployment.


### `scripts/verify_dashboard_api.py`

Checks real operational metadata and probe responses through the deployed frontend proxy.

- **[Imports and setup](../scripts/verify_dashboard_api.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[Remote check program](../scripts/verify_dashboard_api.py#L6):** Defines a small Python program to execute inside the deployed gateway pod; these checks use real Service DNS addresses.
- **[Frontend proxy address](../scripts/verify_dashboard_api.py#L7):** Runs requests through the hosted frontend and nginx `/api` proxy.
- **[Per-service checks](../scripts/verify_dashboard_api.py#L9):** Checks real operational metadata and probe responses through the deployed frontend proxy.
- **[Run check](../scripts/verify_dashboard_api.py#L31):** Uses kubectl exec to run the check in platform-team, and fails the script if verification fails.


### `scripts/verify_dashboard_browser.cjs`

Optional real-browser verification of the deployed dashboard, using Playwright.

- **[Tools](../scripts/verify_dashboard_browser.cjs#L3):** Loads browser automation, assertions, and screenshot support.
- **[Browser startup](../scripts/verify_dashboard_browser.cjs#L8):** Opens an isolated headless browser, optionally using the configured Chrome executable.
- **[Response tracking](../scripts/verify_dashboard_browser.cjs#L14):** Counts actual status polls and captures real service metadata.
- **[Rendered status assertions](../scripts/verify_dashboard_browser.cjs#L28):** Checks owning team, separate health/readiness, model version, and endpoint text for every card.
- **[Automatic polling check](../scripts/verify_dashboard_browser.cjs#L38):** Waits through a polling cycle and proves every check was called at least twice.
- **[Simulated partial outage](../scripts/verify_dashboard_browser.cjs#L45):** Returns 503 only to this browser for forecasting checks. It does not change the actual deployed service.
- **[Live prediction during failure](../scripts/verify_dashboard_browser.cjs#L55):** Enters a known fraud sample and checks a real SageMaker fraud result while the simulated outage remains visible.
- **[Recovery](../scripts/verify_dashboard_browser.cjs#L66):** Removes the simulated failures and verifies forecasting becomes healthy/ready again.
- **[Evidence](../scripts/verify_dashboard_browser.cjs#L72):** Optionally saves a screenshot and prints a JSON verification report.
- **[Cleanup](../scripts/verify_dashboard_browser.cjs#L75):** Closes the temporary browser even if an assertion fails.

### `scripts/verify_frontend_probes.sh`

Checks nginx readiness failure and recovery in a disposable local container.

- **[Test image](../scripts/verify_frontend_probes.sh#L5):** Requires the frontend image to inspect.
- **[Cleanup](../scripts/verify_frontend_probes.sh#L8):** Deletes only the temporary test container when the script exits.
- **[Test container](../scripts/verify_frontend_probes.sh#L10):** Starts nginx with a harmless local gateway-DNS mapping.
- **[Startup wait](../scripts/verify_frontend_probes.sh#L13):** Waits for nginx health before testing readiness.
- **[Failure/recovery scenario](../scripts/verify_frontend_probes.sh#L19):** Checks normal health/readiness, temporarily moves the index page, proves health stays 200 while readiness is 503, then restores the page.
- **[Report](../scripts/verify_frontend_probes.sh#L30):** Prints JSON recording the probe assertions.

### `scripts/verify_kubernetes.py`

Checks real rollout state, Service endpoints, probe configuration, and resource admission behavior.

- **[Imports and setup](../scripts/verify_kubernetes.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[kubectl](../scripts/verify_kubernetes.py#L11):** Runs a Kubernetes command, optionally sending a JSON manifest; raises an error when an expected-success command fails.
- **[get](../scripts/verify_kubernetes.py#L18):** Reads one live Kubernetes object as JSON.
- **[main](../scripts/verify_kubernetes.py#L24):** Checks desired/ready replicas, pod state, matching selectors, ready endpoint addresses, and probes; uses server dry runs to prove defaults and rejection of oversized/over-budget pods. The test pods are never created.

### `scripts/verify_live.py`

Checks served frontend assets, health/readiness, and meaningful SageMaker predictions through the full deployed path.

- **[Imports and setup](../scripts/verify_live.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[Remote check program](../scripts/verify_live.py#L8):** Defines a small Python program to execute inside the deployed gateway pod; these checks use real Service DNS addresses.
- **[Frontend proxy address](../scripts/verify_live.py#L9):** Runs requests through the hosted frontend and nginx `/api` proxy.
- **[Per-service checks](../scripts/verify_live.py#L26):** Checks served frontend assets, health/readiness, and meaningful SageMaker predictions through the full deployed path.
- **[Run check](../scripts/verify_live.py#L49):** Uses kubectl exec to run the check in platform-team, and fails the script if verification fails.


### `scripts/verify_live_validation.py`

Checks malformed requests through the deployed path return safe 422 responses.

- **[Imports and setup](../scripts/verify_live_validation.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[Remote check program](../scripts/verify_live_validation.py#L7):** Defines a small Python program to execute inside the deployed gateway pod; these checks use real Service DNS addresses.
- **[Frontend proxy address](../scripts/verify_live_validation.py#L8):** Runs requests through the hosted frontend and nginx `/api` proxy.
- **[Per-service checks](../scripts/verify_live_validation.py#L21):** Checks malformed requests through the deployed path return safe 422 responses.
- **[Run check](../scripts/verify_live_validation.py#L31):** Uses kubectl exec to run the check in platform-team, and fails the script if verification fails.


### `services/forecasting/.dockerignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `services/forecasting/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../services/forecasting/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../services/forecasting/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../services/forecasting/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../services/forecasting/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../services/forecasting/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../services/forecasting/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../services/forecasting/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `services/forecasting/app/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `services/forecasting/app/main.py`

Compatibility entry point for the shared application.

- **[Import](../services/forecasting/app/main.py#L3):** Re-exports the matching app from `apps/services`; it does not implement another prediction path.

### `services/forecasting/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `services/fraud/.dockerignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `services/fraud/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../services/fraud/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../services/fraud/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../services/fraud/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../services/fraud/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../services/fraud/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../services/fraud/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../services/fraud/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `services/fraud/app/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `services/fraud/app/main.py`

Compatibility entry point for the shared application.

- **[Import](../services/fraud/app/main.py#L3):** Re-exports the matching app from `apps/services`; it does not implement another prediction path.

### `services/fraud/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `services/recommendations/.dockerignore`

Project support configuration.

- **Patterns:** omit generated files, local environments, installed dependencies, or build-irrelevant paths from Git or Docker context.
- **Difference:** .gitignore affects source tracking; .dockerignore affects what is sent into a Docker build.

### `services/recommendations/Dockerfile`

Recipe for building this component’s container image.

- **[Base image](../services/recommendations/Dockerfile#L2):** Starts with the project’s Python runtime.
- **[Working folder](../services/recommendations/Dockerfile#L4):** Runs application commands from `/app`.
- **[Dependencies](../services/recommendations/Dockerfile#L6):** Copies the requirements file, then pip installs its libraries.
- **[Application](../services/recommendations/Dockerfile#L9):** Includes the shared service implementation.
- **[Artifacts/catalog](../services/recommendations/Dockerfile#L11):** Includes trained models and the recommendation catalog for real artifact execution where needed.
- **[Port](../services/recommendations/Dockerfile#L14):** Documents the port served by this image.
- **[Launch](../services/recommendations/Dockerfile#L17):** Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same shared app implementation.

### `services/recommendations/app/__init__.py`

Marks this directory as a Python package so modules can be imported.

- This file contains no application logic.

### `services/recommendations/app/main.py`

Compatibility entry point for the shared application.

- **[Import](../services/recommendations/app/main.py#L3):** Re-exports the matching app from `apps/services`; it does not implement another prediction path.

### `services/recommendations/requirements.txt`

Project support configuration.

- **Dependency list:** lists the Python libraries required by this component.
- **Version constraints:** control allowed package versions.

### `terraform/.terraform.lock.hcl`

Project support configuration.

- **Provider selections:** lock Terraform provider versions.
- **Checksums:** verify the downloaded provider binaries. This is generated dependency metadata, not infrastructure state.

### `terraform/main.tf`

Defines the AWS foundation. These declarations describe what Terraform manages; reading this file does not change AWS.

- **[data "aws_availability_zones" "available"](../terraform/main.tf#L6):** Finds available AWS zones.
- **[locals](../terraform/main.tf#L13):** Selects two zones and builds shared project/environment/owner tags.
- **[resource "aws_vpc" "assessment"](../terraform/main.tf#L26):** Creates the project network, enables DNS, and adds ownership tags.
- **[resource "aws_internet_gateway" "assessment"](../terraform/main.tf#L38):** Provides an internet route for the public subnets.
- **[resource "aws_subnet" "public"](../terraform/main.tf#L49):** Builds public subnets/routing across the selected zones.
- **[resource "aws_route_table" "public"](../terraform/main.tf#L66):** Routes internet-bound traffic through the internet gateway.
- **[resource "aws_route_table_association" "public"](../terraform/main.tf#L80):** Connects each public subnet to that route table.
- **[resource "aws_security_group" "cluster"](../terraform/main.tf#L90):** Defines cluster firewall rules: HTTPS ingress and outbound traffic; these rules do not replace AWS authentication.
- **[resource "aws_iam_role" "cluster"](../terraform/main.tf#L120):** Configures cluster networking or its AWS management role.
- **[resource "aws_iam_role_policy_attachment" "cluster_policy"](../terraform/main.tf#L143):** Attaches the AWS EKS cluster-management policy.
- **[resource "aws_eks_cluster" "assessment"](../terraform/main.tf#L152):** Creates/configures the managed EKS control plane, including version, subnet placement, public API endpoint, and role dependency.
- **[resource "aws_iam_role" "node_group"](../terraform/main.tf#L179):** Defines the EC2 worker-role trust.
- **[resource "aws_iam_role_policy_attachment" "node_group_eks_worker"](../terraform/main.tf#L203):** Gives nodes the EKS worker permissions.
- **[resource "aws_iam_role_policy_attachment" "node_group_eks_cni"](../terraform/main.tf#L209):** Gives the network plugin permissions needed for pod networking.
- **[resource "aws_iam_role_policy_attachment" "node_group_ecr_readonly"](../terraform/main.tf#L215):** Lets nodes pull container images from ECR.
- **[resource "aws_eks_node_group" "main"](../terraform/main.tf#L222):** Defines worker-machine type, scaling range, and rolling-update settings.
- **[resource "aws_eks_access_entry" "student"](../terraform/main.tf#L258):** Optionally creates an EKS access entry for the configured principal.
- **[resource "aws_eks_access_policy_association" "student_cluster_admin"](../terraform/main.tf#L267):** Optionally grants cluster-admin access to that principal.
- **[resource "aws_ecr_repository" "forecasting"](../terraform/main.tf#L285):** Defines the forecasting ECR repository. Enables image scanning, allows mutable tags, and permits deleting a nonempty repository when Terraform destroys it (`force_delete`).
- **[resource "aws_ecr_repository" "fraud"](../terraform/main.tf#L302):** Defines the fraud ECR repository. Enables image scanning, allows mutable tags, and permits deleting a nonempty repository when Terraform destroys it (`force_delete`).
- **[resource "aws_ecr_repository" "recommendations"](../terraform/main.tf#L319):** Defines the recommendations ECR repository. Enables image scanning, allows mutable tags, and permits deleting a nonempty repository when Terraform destroys it (`force_delete`).

### `terraform/outputs.tf`

Values Terraform displays after managing the infrastructure.

- **[output "vpc_id"](../terraform/outputs.tf#L2):** Exports vpc id for operators or other tooling.
- **[output "eks_cluster_name"](../terraform/outputs.tf#L8):** Exports eks cluster name for operators or other tooling.
- **[output "eks_cluster_endpoint"](../terraform/outputs.tf#L14):** Exports eks cluster endpoint for operators or other tooling.
- **[output "eks_cluster_certificate_authority"](../terraform/outputs.tf#L21):** Exports eks cluster certificate authority for operators or other tooling. Terraform marks this output sensitive.
- **[output "ecr_forecasting_repository"](../terraform/outputs.tf#L28):** Exports ecr forecasting repository for operators or other tooling.
- **[output "ecr_fraud_repository"](../terraform/outputs.tf#L34):** Exports ecr fraud repository for operators or other tooling.
- **[output "ecr_recommendations_repository"](../terraform/outputs.tf#L40):** Exports ecr recommendations repository for operators or other tooling.
- **[output "student_eks_principal"](../terraform/outputs.tf#L46):** Exports student eks principal for operators or other tooling.

### `terraform/providers.tf`

Terraform/AWS provider versions and region configuration.

- **[terraform](../terraform/providers.tf#L2):** Sets the minimum Terraform version and compatible AWS-provider version.
- **[provider "aws"](../terraform/providers.tf#L14):** Configures the AWS provider with the input region.

### `terraform/variables.tf`

Inputs used to configure infrastructure names, region, networking, capacity, and optional access.

- **[variable "aws_region"](../terraform/variables.tf#L6):** Chooses the AWS region for infrastructure.
- **[variable "project_name"](../terraform/variables.tf#L13):** Sets the project label/name used by resources.
- **[variable "owner"](../terraform/variables.tf#L20):** Sets the owner name used in resource names and tags.
- **[variable "environment"](../terraform/variables.tf#L27):** Labels the environment, such as dev.
- **[variable "eks_cluster_name"](../terraform/variables.tf#L34):** Supplies the cluster-name suffix; main.tf adds the owner prefix.
- **[variable "eks_version"](../terraform/variables.tf#L41):** Pins the cluster Kubernetes version.
- **[variable "vpc_cidr"](../terraform/variables.tf#L49):** Defines the network address range.
- **[variable "public_subnet_cidrs"](../terraform/variables.tf#L56):** Defines the address ranges for public subnets.
- **[variable "node_instance_type"](../terraform/variables.tf#L63):** Chooses the worker-machine type.
- **[variable "node_desired_size"](../terraform/variables.tf#L70):** Sets the normal desired worker count.
- **[variable "node_min_size"](../terraform/variables.tf#L77):** Sets the minimum worker count.
- **[variable "node_max_size"](../terraform/variables.tf#L84):** Sets the maximum worker count.
- **[variable "student_iam_arn"](../terraform/variables.tf#L92):** Optionally identifies the AWS principal granted cluster-admin access; an empty value skips that grant.

### `tests/test_deployment.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_deployment.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_rendered_deployment_chain](../tests/test_deployment.py#L12):** Renders manifests without AWS, then checks namespaces, selectors, images, ConfigMaps, ServiceAccounts, probes, budgets, versions, and ingress routes.

### `tests/test_integration.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_integration.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_validation](../tests/test_integration.py#L22):** Checks malformed business requests return 422.
- **[test_missing_artifact_liveness](../tests/test_integration.py#L27):** Checks that a missing artifact leaves the process alive but makes readiness and prediction fail safely.
- **[test_sagemaker_failure_never_falls_back](../tests/test_integration.py#L35):** Checks that failed remote inference returns an error instead of silently using a local model.
- **[test_sagemaker_success_and_invalid_output](../tests/test_integration.py#L47):** Checks valid remote output is labeled SageMaker and invalid scores are rejected.
- **[test_forecast_lag_order](../tests/test_integration.py#L62):** Checks that the newest history value becomes lag 1 and each forecast updates the next prediction’s history.
- **[test_recommendation_encoding_and_probability](../tests/test_integration.py#L72):** Checks catalog-wide category/item encoding and ranking by predicted click probability.
- **[test_gateway_to_real_model](../tests/test_integration.py#L90):** Connects the gateway to real local service apps in memory, proving route-to-model integration without an AWS/network dependency.
- **[test_gateway_to_real_model → downstream](../tests/test_integration.py#L92):** Sends one HTTP request to a downstream API using an explicit timeout.

### `tests/test_sagemaker_deployment.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_sagemaker_deployment.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_serverless_has_no_always_on_instances](../tests/test_sagemaker_deployment.py#L6):** Checks the endpoint configuration uses on-demand serverless settings rather than fixed instances.
- **[test_workload_permissions_are_service_specific](../tests/test_sagemaker_deployment.py#L15):** Checks each role can invoke only its endpoint and trusts only the intended cluster/namespace/service account.
- **[test_bind_does_not_change_files_before_verified](../tests/test_sagemaker_deployment.py#L27):** Checks a failed endpoint invocation prevents Kubernetes configuration from being written.
- **[test_bind_assigns_correct_service_accounts_and_endpoints](../tests/test_sagemaker_deployment.py#L38):** Checks verified endpoints are bound to the correct configuration and workload identity.
- **[test_identity_migration_keeps_old_roles_and_rejects_wrong_binding](../tests/test_sagemaker_deployment.py#L63):** Checks migration uses dedicated roles and refuses an unexpected existing identity association.

### `tests/test_sagemaker_serving.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_sagemaker_serving.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_hosting_contract](../tests/test_sagemaker_serving.py#L12):** Checks `/ping` and `/invocations` behave correctly, and hosted output matches direct model output.
- **[test_ping_checks_artifact](../tests/test_sagemaker_serving.py#L24):** Checks that an unavailable artifact makes SageMaker’s ping fail.

### `tests/test_service_metadata.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_service_metadata.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[test_metadata_reports_actual_configuration_without_invoking_aws](../tests/test_service_metadata.py#L14):** Checks all metadata values match configuration and no inference request is made.
- **[test_metadata_remains_available_when_runtime_is_not_ready](../tests/test_service_metadata.py#L28):** Checks configuration information remains readable even when inference readiness fails.

### `tests/test_validation_gaps.py`

Automated tests for this part of the platform.

- **[Imports and setup](../tests/test_validation_gaps.py#L2):** Brings in the libraries, shared code, and test or runtime settings needed below.
- **[make_app](../tests/test_validation_gaps.py#L25):** Builds a service API around a replaceable runtime for tests.
- **[test_nonfinite_request_is_safe_422](../tests/test_validation_gaps.py#L33):** Checks NaN/Infinity input gets a safe, serializable 422 response.
- **[test_gateway_rejects_nonfinite_before_downstream](../tests/test_validation_gaps.py#L52):** Checks nested invalid numbers are rejected before any downstream call.
- **[test_readiness_requires_each_configuration_value](../tests/test_validation_gaps.py#L63):** Checks missing endpoint and missing region separately for every service.
- **[test_model_input_error_is_422_without_private_details](../tests/test_validation_gaps.py#L78):** Checks hosted input errors become safe 422 responses through both the service and gateway.
- **[test_model_input_error_is_422_without_private_details → downstream](../tests/test_validation_gaps.py#L84):** Sends one HTTP request to a downstream API using an explicit timeout.
- **[test_runtime_or_permission_errors_remain_502](../tests/test_validation_gaps.py#L97):** Checks server/permission failures remain 502 and do not leak private messages.
- **[test_logging_contains_service_team_and_safe_request_context](../tests/test_validation_gaps.py#L108):** Checks service/team, sanitized request ID, status, and timing appear in the JSON request log.

## Local/generated files also present in the directory

- **`.venv/` and `services/fraud/venv/`:** installed Python interpreters, activation scripts, and third-party package code. They support execution; they are not this project’s authored implementation.
- **`dashboard/frontend/node_modules/`:** downloaded React/Vite/lint dependencies; package.json and the lockfile describe their role.
- **`dashboard/frontend/dist/`:** generated production HTML/JS/CSS compiled from the dashboard source.
- **`__pycache__/`, `.pytest_cache/`, and `.vite/`:** generated caches that speed development/tests.
- **`terraform/.terraform/`:** downloaded providers and working metadata. Terraform state/plan files track real resource mappings or proposed changes; do not present them as application source or publish their contents.
- **`.env` and other local environment files:** local settings, potentially including secrets; this guide does not reproduce their values.
- **`.git/`:** repository history and tracking internals.
- **`*.log`, including `ci-36083070014.log`:** recorded command/workflow output for troubleshooting, not code to deploy.
- **`.DS_Store`:** operating-system folder metadata.

## Five short presentation lines

1. “My frontend shows service status and model metadata from APIs, and polls each service independently.”
2. “The gateway routes each request to exactly the matching FastAPI adapter.”
3. “I separate validation, feature preparation, and AWS invocation, so tests can replace AWS.”
4. “Kubernetes runs the applications with scoped identity, resource budgets, and separate startup, liveness, and readiness checks.”
5. “The trained models execute inside SageMaker, and my verification reports show the real results returning through the deployed frontend.”

Coverage: 163 project-owned files, plus the generated/local categories above.
