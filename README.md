# PowerDNS NS

Descriptors that installs a PowerDNS chart from "https://gatici.github.io/helm-repo/" repo.

There is one VNF (powerdns_knf) with only one KDU.

There is one NS that connects the VNF to a mgmt network

## Download Packages

```bash
git clone https://github.com/gatici/powerdns_descriptors.git && cd powerdns_descriptors
```

## Create the VIM Account

```bash
# This is dummy vim account
export VIM_ACCOUNT=k8s-vim
osm vim-create --name $VIM_ACCOUNT \
               --account_type dummy \
               --user dummy \
                --password dummy \
                --auth_url "http://dummy" \
                --tenant dummy
```

## Add K8s Cluster

```bash
# kubeconfig.yaml exists in the HOME directory
export k8s_net=<K8s cluster network>  # osm-ext
osm k8scluster-add --creds ~/kubeconfig.yaml \
                     --vim k8s-vim \
                     --k8s-nets "{k8s_net: $k8s_net}" \
                     --version 1.24  \
                     k8s-cluster
```

## Add Helm Repository

```bash
osm repo-add --type helm-chart --description "Repository for Powerdns helm Chart" osm-helm https://gatici.github.io/helm-repo/
```

## Build the charm

```bash
# Install charmcraft
sudo snap install charmcraft --classic
pushd powerdns_knf/charms/ops/powerdns-operator
# Pack charm
charmcraft pack
# Copy charm under VNFD/charms folder
cp powerdns-operator_ubuntu-20.04-amd64.charm  ../../
popd
```

## Onboarding and instantiation

```bash
export VNF_NAME=powerdns
export KDU_NAME=powerdns
# Define the NS name
export NS_NAME=<ns name>
```

```bash
osm nfpkg-create powerdns_knf
osm nspkg-create powerdns_ns
osm ns-create --ns_name $NS_NAME --nsd_name powerdns_ns --vim_account $VIM_ACCOUNT --config "{vld: [ {name: mgmtnet, vim-network-name: $k8s_net}]}"
# Check NS status
osm ns list
```

## Test Day2 Actions: add-zone, add-domain

```bash
# Add Zone Action
# Define zone such as "example.org."
ZONE=<zone> 
OP_ID=`osm ns-action --action_name add-zone --vnf_name $VNF_NAME --kdu_name $KDU_NAME --params "{"zone_name": $ZONE}" $NS_NAME`
# Check operation status
osm ns-op-show $OP_ID
# Add Domain Action
# Define domain such as "test."
DOMAIN=<domain> 
# Define ip such as "192.168.2.32"
IP=<ip>
OP_ID=`osm ns-action --action_name add-domain --vnf_name $VNF_NAME --kdu_name $KDU_NAME  --params "{'zone_name': $ZONE, 'subdomain': $DOMAIN, 'ip': $IP}" $NS_NAME`
# Check operation status
osm ns-op-show $OP_ID
```

## Testing PowerDNS server

```bash
VNF_ID=`osm vnf-list --ns $NS_NAME | grep powerdns | awk '{print $2}'`
export DNS_IP=`osm vnf-show $VNF_ID --literal | yq -e '.kdur[0].services[] | select(.name | endswith("-tcp")) | .external_ip' | tr -d \"[]' '`
RECORD=<domain><zone> 
# Sample record: "test.example.org"
dig @${DNS_IP} +tcp $RECORD
```

## Test Day2 Actions: delete-domain, delete-zone

```bash
# Delete Domain
OP_ID=`osm ns-action --action_name delete-domain --vnf_name $VNF_NAME --kdu_name $KDU_NAME  --params "{'zone_name': $ZONE, 'subdomain': $DOMAIN}" $NS_NAME`
osm ns-op-show $OP_ID
dig @${DNS_IP} +tcp ${RECORD}
# Delete Zone
OP_ID=`osm ns-action --action_name delete-zone --vnf_name $KDU_NAME --kdu_name $KDU_NAME  --params "{'zone_name': $ZONE}" $NS_NAME`
osm ns-op-show $OP_ID
```

## Upgrade Operation: Scale Out

```bash
OP_ID=`osm ns-action --action_name upgrade --vnf_name $VNF_NAME  --kdu_name $KDU_NAME --params "{'replicaCount':'3',}" $NS_NAME`
osm ns-op-show $OP_ID --literal | yq .operationState
osm vnf-show $VNF_ID --kdu $KDU_NAME | yq .config.replicaCount
```

## Rollback Operation: Scale In

```bash
OP_ID=`osm ns-action --action_name rollback --vnf_name $VNF_NAME --kdu_name $KDU_NAME $NS_NAME`
osm ns-op-show $OP_ID --literal | yq .operationState
osm vnf-show $VNF_ID --kdu $KDU_NAME | yq .config.replicaCount 
```
