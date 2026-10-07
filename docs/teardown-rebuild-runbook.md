# Presentation: destroy, rebuild, verify, repeat

For one complete cycle, run the command blocks in **sections 1–7**, in order, in the same terminal, except the final port-forward (a separate terminal). Section 8 tells you how to repeat; it is not another step to execute immediately. **These instructions delete the live platform before rebuilding it. Do not run a separate `terraform destroy` first.** Rehearse the full cycle well before presenting; AWS provisioning, image builds, and endpoint creation have variable completion times. Keep a working deployment for the presentation if you cannot finish a rehearsal beforehand.

## What this restores

The goal is the same application and trained models: the deployed React dashboard, gateway, three FastAPI services, and three real SageMaker inference endpoints, reached at `http://127.0.0.1:8080` through a frontend port-forward. AWS resource IDs, IP addresses, image digests, release labels, and model/config release names change. The completed rehearsal rebuilt the foundation on EKS 1.34 and AL2023. These are the settings used below for future cycles.

The sequence has been checked for Terraform validity and shell/Python syntax. A destroy/rebuild rehearsal reached successful application rollout and real predictions through the deployed frontend/gateway for all three services. Future execution still depends on AWS permissions, capacity, network access, and the live checks below. You confirmed that the browser checks and remaining validation, dashboard metadata, and ownership checks also completed. The rehearsal is complete. A failed command is a stop condition; do not continue past it. Plan review and typing the SageMaker deletion phrase are intentional steps, not missing configuration.

## What disappears and what stays

| Component | Managed by | Full-cycle action |
| --- | --- | --- |
| VPC, public subnets/routes, security group | Terraform | Destroy and recreate |
| EKS control plane, managed workers, their IAM roles | Terraform | Destroy and recreate |
| Three ECR repositories and **every image inside them** | Terraform (`force_delete=true`) | Destroy; rebuild all five application images and the SageMaker image |
| Three SageMaker endpoints, endpoint configs, models | `scripts/deploy_sagemaker.py` | Delete the exact owned hosting resources first; reprovision after ECR |
| SageMaker execution role and workload invocation roles | Deployment script | Retain; provisioning checks and reuses them |
| Pod Identity agent and associations | Deployment script, attached to EKS | Removed with cluster; recreate on the new cluster |
| Kubernetes objects | Application manifests/scripts | Lost with cluster; deploy again |
| Source, trained artifacts, local Terraform state | Local project | Preserve |

Terraform does **not** destroy SageMaker. Keeping the existing endpoints while deleting their ECR hosting image is not a reliable rebuild strategy. The hosting container already includes the trained artifacts in `ml/models/`; no training job is needed. The retained IAM roles are intentionally outside this destroy cycle. Do not run `scripts/cleanup-ecr.sh`, delete the state, or use routine `-target` destruction.

Verified while preparing this guide: account `388691194728`, IAM user `Anthony`, Terraform workspace `default`, rebuilt cluster `anthony-assessment4-eks` on 1.34 with AL2023 workers, all three project endpoints InService. These are observations, not a guarantee of future state. Existing doubled names such as `anthony-anthony-assessment4-ng` match state; do not rename them during teardown.

## 1. Prepare and check the account

Use the same authorized AWS identity/profile that owns the existing deployment. Docker Desktop must be running. Install Terraform, AWS CLI, kubectl, Docker Buildx, Python 3.11, and Node/npm beforehand. No new AWS access key is needed if your existing profile works. If using SSO, log in to that profile first.

Use the normal VS Code terminal (zsh worked during rehearsal). **Run each command individually and wait for its prompt before the next.** Do not paste the whole document. Copy only command text, excluding Markdown backticks. For a multiline Python block, copy the entire block through its final `PY`; for the settings block include the final `VARS`.

No shell switch or `set -e`/`set -u` is needed. Those options caused prompt errors and terminal exits during rehearsal. Stop manually whenever a command reports an error; use the recovery section before continuing.

```bash
cd /Users/anthonycarlock/codeplatoon/assessment-iv-ml-platform
```

```bash
export AWS_REGION=us-east-1
```

```bash
export AWS_DEFAULT_REGION=us-east-1
```

```bash
export AWS_ACCOUNT_ID=388691194728
```

```bash
export EKS_CLUSTER_NAME=anthony-assessment4-eks
```

```bash
aws sts get-caller-identity
```

```bash
# Stop if this does not show account 388691194728 and your intended identity.
test "$(aws sts get-caller-identity --query Account --output text)" = "$AWS_ACCOUNT_ID"
```

```bash
terraform -chdir=terraform init
```

```bash
terraform -chdir=terraform workspace show
```

```bash
terraform -chdir=terraform state list
```

```bash
# Stop unless this is the expected workspace and only this project's resources.
if [ ! -x .venv/bin/python ]; then
  python3.11 -m venv .venv
fi
```

```bash
.venv/bin/python -m pip install -r requirements.txt
```

```bash
.venv/bin/python -m pytest -q apps tests
```

```bash
(cd dashboard/frontend && npm ci && npm test && npm run lint && npm run build)
```

```bash
docker info >/dev/null
```

The commands create the Python environment if needed. Save your source changes and trained artifacts before deleting infrastructure. Do not commit AWS credentials, state, or saved plans. Expected checks: account `388691194728`, identity `Anthony`, workspace `default`, project EKS/ECR/network resources in state, 107 Python tests passing, 3 frontend tests passing, no lint errors, successful frontend build, and Docker server information. npm's dependency audit notice is separate from test/build success; inspect it before applying package upgrades.

Create a private, ignored backup directory. Keep this terminal open; later commands use `CYCLE_DIR`.

```bash
umask 077
```

```bash
export CYCLE_DIR="$PWD/.presentation-backups/$(date -u +%Y%m%dT%H%M%SZ)"
```

```bash
mkdir -p "$CYCLE_DIR"
```

```bash
printf '%s\n' "$CYCLE_DIR" > .presentation-backups/current-cycle-path.txt
```

```bash
terraform -chdir=terraform state pull > "$CYCLE_DIR/before.tfstate"
```

```bash
# Save the actual live version/AMI for this cycle's destruction, including repeats.
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['CYCLE_DIR'])
state = json.loads((root / 'before.tfstate').read_text())
managed = [r for r in state['resources'] if r['mode'] == 'managed']
cluster = next(r for r in managed if r['type'] == 'aws_eks_cluster' and r['name'] == 'assessment')['instances'][0]['attributes']
nodes = next(r for r in managed if r['type'] == 'aws_eks_node_group' and r['name'] == 'main')['instances'][0]['attributes']
assert cluster['name'] == 'anthony-assessment4-eks'
assert nodes['cluster_name'] == cluster['name']
values = {'eks_version': cluster['version'], 'node_ami_type': nodes['ami_type']}
(root / 'destroy.tfvars.json').write_text(json.dumps(values, indent=2) + '\n')
print('Current infrastructure settings:', values)
PY
```

```bash
.venv/bin/python scripts/deploy_sagemaker.py status
```

```bash
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME"
```

```bash
kubectl config current-context
```

```bash
kubectl get services,ingresses -A
```

Check the context is this cluster. If the optional public frontend was deployed, remove it **while the cluster still exists**:

```bash
kubectl delete -f k8s/exposure/frontend-public.yaml --ignore-not-found
```

If you installed an ingress controller or other LoadBalancer services separately, remove their project-owned exposure resources too and verify their AWS load balancers are gone before destroying EKS. Do not delete other workloads blindly. The normal deployment uses a frontend port-forward and needs no public load balancer. See [AWS's cluster deletion guidance](https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html).

### Check AWS for leftover load balancers

The rehearsal found an orphaned nginx-controller network load balancer even though Kubernetes listed only ClusterIP services and ingresses with empty addresses. Check AWS before destroying the cluster/network. This command is read-only and finds load balancers in the current project VPC:

```bash
export PROJECT_VPC=$(terraform -chdir=terraform output -raw vpc_id)
```

```bash
aws elbv2 describe-load-balancers --region us-east-1 --query "LoadBalancers[?VpcId=='${PROJECT_VPC}'].{Name:LoadBalancerName,Arn:LoadBalancerArn}" --output json
```

If the result is `[]`, continue to section 2. Otherwise, run this complete block. It checks ownership before offering cleanup, discovers the current ARNs, and waits for network interfaces to disappear. It never uses the old rehearsal ARN. Do not proceed past an error.

```bash
.venv/bin/python - <<'PY'
import os, time
import boto3
session = boto3.Session(region_name='us-east-1')
assert session.client('sts').get_caller_identity()['Account'] == '388691194728'
vpc = os.environ['PROJECT_VPC']
elb = session.client('elbv2')
ec2 = session.client('ec2')
owned = []
for page in elb.get_paginator('describe_load_balancers').paginate():
    for lb in page['LoadBalancers']:
        if lb['VpcId'] != vpc:
            continue
        arn = lb['LoadBalancerArn']
        tags = {t['Key']: t['Value'] for t in elb.describe_tags(ResourceArns=[arn])['TagDescriptions'][0]['Tags']}
        assert tags.get('kubernetes.io/cluster/anthony-assessment4-eks') == 'owned' or (tags.get('Owner') == 'anthony' and tags.get('Project') == 'anthony-assessment4'), (arn, tags)
        print('Project load balancer:', arn, tags)
        owned.append(arn)
if owned:
    with open('/dev/tty') as terminal:
        print('Type DELETE project load balancers to proceed: ', end='', flush=True)
        assert terminal.readline().strip() == 'DELETE project load balancers'
    for arn in owned:
        elb.delete_load_balancer(LoadBalancerArn=arn)
    elb.get_waiter('load_balancers_deleted').wait(LoadBalancerArns=owned)
    for attempt in range(120):
        interfaces = ec2.describe_network_interfaces(Filters=[{'Name':'vpc-id','Values':[vpc]}])['NetworkInterfaces']
        pending = [i['NetworkInterfaceId'] for i in interfaces if i.get('InterfaceType') in ('network_load_balancer','load_balancer') or i.get('Description','').startswith('ELB ')]
        if not pending:
            break
        print('Waiting for load-balancer interfaces:', pending, flush=True)
        time.sleep(5)
    else:
        raise RuntimeError('Load-balancer interfaces remain; inspect AWS before Terraform destroy')
print('Load-balancer cleanup complete.')
PY
```

If a live ingress controller still owns a LoadBalancer Service, delete that project-owned Kubernetes exposure first so it cannot recreate the AWS load balancer. Do not delete AWS-managed network interfaces manually. This check covers ELBv2 load balancers used in the rehearsal; separately installed classic ELBs or other AWS workloads require their own ownership-checked cleanup.

## 2. Record the exact SageMaker resources before deletion

This block is read-only in AWS. It checks ownership for every endpoint/config/model and records the names in the private cycle directory. It avoids assuming the model/config is always named `sm-v1` on subsequent runs.

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
import boto3
session = boto3.Session(region_name='us-east-1')
assert session.client('sts').get_caller_identity()['Account'] == '388691194728'
sm = session.client('sagemaker')
rows = []
for service in ('fraud', 'forecasting', 'recommendations'):
    name = f'anthony-assessment4-{service}-sagemaker'
    endpoint = sm.describe_endpoint(EndpointName=name)
    config = sm.describe_endpoint_config(EndpointConfigName=endpoint['EndpointConfigName'])
    assert len(config['ProductionVariants']) == 1
    model = sm.describe_model(ModelName=config['ProductionVariants'][0]['ModelName'])
    for arn in (endpoint['EndpointArn'], config['EndpointConfigArn'], model['ModelArn']):
        tags = {t['Key']: t['Value'] for t in sm.list_tags(ResourceArn=arn)['Tags']}
        assert tags.get('Owner') == 'anthony' and tags.get('Project') == 'anthony-assessment4', arn
    assert config['EndpointConfigName'].startswith(f'anthony-assessment4-{service}-')
    assert model['ModelName'].startswith(f'anthony-assessment4-{service}-')
    rows.append({'endpoint': name, 'config': config['EndpointConfigName'], 'model': model['ModelName']})
path = Path(os.environ['CYCLE_DIR']) / 'sagemaker-resources.json'
assert not path.exists(), 'Use the existing inventory to recover an interrupted cycle; do not overwrite it.'
path.write_text(json.dumps(rows, indent=2) + '\n')
print(path.read_text())
PY
```

Stop if checks fail or names differ from this project. These models/configs were created for these three endpoints; if you have subsequently shared them with additional endpoints, resolve that dependency before deletion.

## 3. Delete only the recorded SageMaker hosting resources

**Destructive:** the following removes the three endpoints, their active endpoint configs, and their active models. This stops inference until the rebuild. It leaves artifacts in your project and retains IAM roles.

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
import boto3
session = boto3.Session(region_name='us-east-1')
assert session.client('sts').get_caller_identity()['Account'] == '388691194728'
sm = session.client('sagemaker')
rows = json.loads((Path(os.environ['CYCLE_DIR']) / 'sagemaker-resources.json').read_text())
assert len(rows) == 3
expected = {f'anthony-assessment4-{s}-sagemaker' for s in ('fraud', 'forecasting', 'recommendations')}
assert {r['endpoint'] for r in rows} == expected
# Recheck resource ownership immediately before any deletion.
for row in rows:
    resources = (
        sm.describe_endpoint(EndpointName=row['endpoint'])['EndpointArn'],
        sm.describe_endpoint_config(EndpointConfigName=row['config'])['EndpointConfigArn'],
        sm.describe_model(ModelName=row['model'])['ModelArn'],
    )
    for arn in resources:
        tags = {t['Key']: t['Value'] for t in sm.list_tags(ResourceArn=arn)['Tags']}
        assert tags.get('Owner') == 'anthony' and tags.get('Project') == 'anthony-assessment4', arn
print(json.dumps(rows, indent=2))
with open('/dev/tty') as terminal:
    print('Type DELETE anthony-assessment4 to proceed: ', end='', flush=True)
    assert terminal.readline().strip() == 'DELETE anthony-assessment4'
for row in rows:
    sm.delete_endpoint(EndpointName=row['endpoint'])
for row in rows:
    sm.get_waiter('endpoint_deleted').wait(EndpointName=row['endpoint'])
    sm.delete_endpoint_config(EndpointConfigName=row['config'])
    sm.delete_model(ModelName=row['model'])
    print('Deleted hosting resources:', row['endpoint'])
PY
```

If interrupted or a waiter times out, use the saved JSON and AWS console/CLI to check which exact resources still exist. Finish their deletion before continuing. Do not blindly rerun the whole block: it deliberately fails if a resource is already absent. No account-wide SageMaker cleanup is required.

## 4. Preview and destroy the Terraform foundation

The version and node-image settings were captured from current state in section 1. The same commands therefore work for the first cycle and subsequent cycles. The other project inputs retain the audited repository defaults; if you intentionally changed those inputs, preserve those values too before planning.

```bash
terraform -chdir=terraform plan -destroy -var-file="$CYCLE_DIR/destroy.tfvars.json" -out="$CYCLE_DIR/destroy.tfplan"
```

```bash
terraform -chdir=terraform show "$CYCLE_DIR/destroy.tfplan"
```

Review every deletion: this project's EKS cluster/workers, VPC/network resources, cluster/node IAM roles, and three ECR repositories. **All application and hosting images will be lost.** Stop for unexpected resources or dependencies. Then execute the reviewed plan:

```bash
terraform -chdir=terraform apply "$CYCLE_DIR/destroy.tfplan"
```

```bash
terraform -chdir=terraform state list
```

```bash
aws eks list-clusters --region "$AWS_REGION"
```

```bash
aws ecr describe-repositories --region "$AWS_REGION" --query 'repositories[].repositoryName'
```

```bash
aws sagemaker list-endpoints --region "$AWS_REGION" --name-contains anthony-assessment4
```

Applying a saved destroy plan is the reviewed-plan equivalent of `terraform destroy`. There is only one destruction path in this guide: review the saved plan and apply it. See [Terraform destroy](https://developer.hashicorp.com/terraform/cli/commands/destroy).

Successful destruction leaves no managed resources in this workspace; data-source entries may remain. Other projects may still appear in account listings. Do not delete those. If Terraform fails, fix the reported dependency and re-plan from the remaining state; never erase state to hide a failed deletion.

### Recover from a partially completed destroy

During rehearsal, an internet-gateway deletion timed out with `DependencyViolation` while an orphaned load balancer still held public addresses. Both subnets eventually deleted after the load balancer was removed. Terraform correctly retained only the gateway/VPC in state. Once the dependency cleared, a fresh plan finished destruction:

```bash
terraform -chdir=terraform state list
```

```bash
terraform -chdir=terraform plan -destroy -var-file="$CYCLE_DIR/destroy.tfvars.json" -out="$CYCLE_DIR/destroy-retry.tfplan"
```

```bash
terraform -chdir=terraform show "$CYCLE_DIR/destroy-retry.tfplan"
```

```bash
# Apply only after verifying that the remaining deletions belong to this project.
terraform -chdir=terraform apply "$CYCLE_DIR/destroy-retry.tfplan"
```

```bash
terraform -chdir=terraform state list
```

Never reuse the original saved plan after a partial apply, and never delete state. Only start the rebuild after there are no managed resources left.

## 5. Rebuild the foundation with a supported node image

Only after the original foundation is fully destroyed, create these explicit rebuild settings. AL2023 is selected through the new `node_ami_type` input; its default remains AL2 so adding the input alone does not replace the current workers. AWS [stopped publishing EKS AL2 images](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) in November 2025.

The example selects EKS 1.34, which the AWS API reported in standard support when this guide was prepared. Check availability before each future rehearsal; choose a supported version and test it. This recreates the cluster after destruction. Preserve the same 1.34/AL2023 settings for this rehearsed procedure.

```bash
aws eks describe-cluster-versions --region "$AWS_REGION" \
  --query 'clusterVersions[].{version:clusterVersion,status:status}' --output table
```

```bash
cat > "$CYCLE_DIR/rebuild.tfvars" <<'VARS'
aws_region       = "us-east-1"
owner            = "anthony"
project_name     = "anthony-assessment4"
eks_cluster_name = "assessment4-eks"
eks_version      = "1.34"
node_ami_type    = "AL2023_x86_64_STANDARD"
student_iam_arn  = ""
VARS
```

```bash
terraform -chdir=terraform fmt -check
```

```bash
terraform -chdir=terraform validate
```

```bash
terraform -chdir=terraform plan -var-file="$CYCLE_DIR/rebuild.tfvars" -out="$CYCLE_DIR/create.tfplan"
```

```bash
terraform -chdir=terraform show "$CYCLE_DIR/create.tfplan"
```

```bash
# Review names, Owner/Project tags, node count, versions and AMI before applying.
terraform -chdir=terraform apply "$CYCLE_DIR/create.tfplan"
```

```bash
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME"
```

```bash
kubectl get nodes
```

```bash
kubectl wait --for=condition=Ready nodes --all --timeout=600s
```

Use the same cluster-creator identity to administer the rebuilt cluster. The current configuration uses ConfigMap authentication and leaves optional access entries disabled; setting `student_iam_arn` requires configuring an access-entry-compatible authentication mode first. If `kubectl` returns Unauthorized, fix identity/access before proceeding; do not destroy a healthy cluster to solve credentials.

**Keep this rebuild variable file.** Use it for subsequent infrastructure changes. Each repeat of this runbook captures the current version/AMI again for destruction. Running an ordinary apply with defaults against the rebuilt cluster would propose the old version/AMI.

## 6. Rebuild and deploy SageMaker hosting

Choose a new release for every successful cycle. The Terraform step must finish first because the build needs ECR and provisioning needs EKS.

```bash
export IMAGE_TAG="presentation-$(date -u +%Y%m%dT%H%M%SZ)"
```

```bash
export SM_RELEASE="sm-${IMAGE_TAG}"
```

```bash
.venv/bin/python - <<'PY'
import os, shlex
from pathlib import Path
keys = ('CYCLE_DIR','AWS_REGION','AWS_DEFAULT_REGION','AWS_ACCOUNT_ID','EKS_CLUSTER_NAME','IMAGE_TAG','SM_RELEASE')
path = Path(os.environ['CYCLE_DIR']) / 'session.env'
path.write_text(''.join(f'export {k}={shlex.quote(os.environ[k])}\n' for k in keys))
print('Saved session variables:', path)
PY
```

```bash
bash scripts/build_sagemaker.sh
```

```bash
export SM_DIGEST="$(aws ecr describe-images --region "$AWS_REGION" \
  --repository-name anthony-assessment4-fraud \
  --image-ids "imageTag=sagemaker-${IMAGE_TAG}" \
  --query 'imageDetails[0].imageDigest' --output text)"
```

```bash
export SM_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/anthony-assessment4-fraud@${SM_DIGEST}"
```

```bash
.venv/bin/python scripts/deploy_sagemaker.py provision --image "$SM_IMAGE" --release "$SM_RELEASE"
```

```bash
aws eks describe-addon --region us-east-1 --cluster-name anthony-assessment4-eks --addon-name eks-pod-identity-agent --query 'addon.status' --output text
```

Expected: `ACTIVE`. If it is still creating, wait and rerun that read-only command. Then check endpoint status:

```bash
.venv/bin/python scripts/deploy_sagemaker.py status
```

Wait until **all three endpoints are `InService`** with no failure reason. Rerun `status` about once per minute while they are creating; do not rerun `provision` just because creation is taking time. Then run:

```bash
.venv/bin/python scripts/deploy_sagemaker.py verify
```

Stop if any endpoint is not InService, the addon is not ACTIVE, or verification fails. Inspect endpoint `FailureReason` and CloudWatch logs rather than proceeding. If a cold-start request fails, rerun verification after checking endpoint status. Provisioning reuses the scoped IAM roles and recreates Pod Identity associations; do not put static AWS keys in Kubernetes. The checked-in ConfigMaps already refer to the stable endpoint names and SageMaker provider, so `bind` is unnecessary and would rewrite commented YAML.

Long hosting model/config names are now shortened deterministically to the 63-character SageMaker limit, while existing short names stay unchanged. This fixed a forecasting provisioning failure during the rehearsal.

If provisioning was interrupted, retry it with the **same image digest and release**. Choosing a new release while an existing endpoint references the previous one is deliberately rejected by the script. A new release is for the next completed destroy/rebuild cycle.

## 7. Build applications, deploy, and verify the actual path

```bash
bash scripts/build.sh
```

```bash
bash scripts/deploy.sh
```

```bash
.venv/bin/python scripts/verify_kubernetes.py
```

```bash
.venv/bin/python scripts/verify_live.py
```

```bash
.venv/bin/python scripts/verify_live_validation.py
```

```bash
.venv/bin/python scripts/verify_dashboard_api.py
```

```bash
.venv/bin/python scripts/audit_aws_ownership.py
```

These checks cover rollout, probes, service endpoints, namespace policies, malformed requests, dashboard metadata, ownership, and real predictions through the deployed frontend proxy. Do not declare the rebuild complete if any check fails. Resolve failures using `kubectl describe pod`, workload logs, SageMaker status/logs, and Pod Identity permissions. New pods may briefly wait for IAM propagation. Kubernetes rollout timeouts can be retried after checking status; they do not require another infrastructure rebuild.

In a separate terminal:

```bash
cd /Users/anthonycarlock/codeplatoon/assessment-iv-ml-platform
```

```bash
kubectl -n platform-team port-forward --address 127.0.0.1 svc/frontend-service 8080:80
```

Open **http://127.0.0.1:8080**. If port 8080 is occupied by an old port-forward, stop that command with Ctrl+C first. The tunnel reaches the deployed nginx/React frontend; it is not Vite or local inference. Show team ownership, separate health/readiness, endpoint/version information, and live polling. Submit all three prediction forms and show `provider: sagemaker` in the API responses. The full path is browser → deployed frontend → gateway → FastAPI → SageMaker → browser.

## 8. Repeat or stop

For another complete cycle, stop the port-forward with Ctrl+C, then run **sections 1–7 again**. Section 1 creates a new private backup directory and captures the current Terraform version/AMI; section 2 records the current SageMaker release names; section 6 creates a new image tag/release. No placeholder path needs to be filled in for a repeat.

For final shutdown after the presentation, run sections **1–4 only**, then stop. That deletes active hosting and the Terraform foundation. The intentionally retained SageMaker/workload IAM roles and local source/state backups remain. Previously abandoned SageMaker releases or independently created load balancers require their own scoped cleanup if you created them; this runbook removes the active resources inventoried for this project.

## Recovery: terminal and interrupted steps

- `quote>`: press Ctrl+C. The command has an unmatched quote. Copy the entire command again; do not append a quote to accumulated text.
- `>` during `if` or `heredoc>` during a multiline block: the shell is waiting for `fi`, `PY`, or `VARS`. This is normal until the closing line is entered.
- `requirements.txt`/`tests`/`dashboard/frontend` not found: run the project `cd` command from section 1, then `pwd` and `ls requirements.txt tests dashboard/frontend terraform`.
- `RPROMPT: parameter not set`: run `set +u`. If the terminal closed, open a new terminal and use this guide without `set -u` or `set -e`.
- `Still creating...`/`Still destroying...`: keep that Terraform command running; do not start a concurrent apply/destroy. Inspect reported errors when it finishes.
- Docker image push takes time: wait for successful completion and the returned prompt. The SageMaker build also prints its digest.
- Provisioning failure: fix the reported cause, then retry the same `provision` command with the same release and digest. The 63-character name issue found during rehearsal is fixed in the script.
- Port-forward `Handling connection for 8080`: normal browser traffic. Leave the command running. Stop an old port-forward with Ctrl+C if the port is occupied.

If your original terminal closes after the release variables have been saved, open a new terminal and restore them. This does not create resources or start a new cycle:

```bash
cd /Users/anthonycarlock/codeplatoon/assessment-iv-ml-platform
```

```bash
export CYCLE_DIR=$(cat .presentation-backups/current-cycle-path.txt)
```

```bash
source "$CYCLE_DIR/session.env"
```

Recompute `SM_DIGEST` and `SM_IMAGE` using section 6 before retrying provisioning. If `session.env` does not exist yet, restore the five AWS/cluster exports from section 1 and keep the existing `CYCLE_DIR`; do not repeat inventory or deletion blindly. Use the saved inventories and Terraform state to determine which step completed.
