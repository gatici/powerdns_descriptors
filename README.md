# PowerDNS NS

Descriptors that installs a PowerDNS chart from "https://gatici.github.io/helm-repo/" repo.

There is one VNF (powerdns_knf) with only one KDU.

There is one NS that connects the VNF to a mgmt network

## Add Helm Repository

```bash
osm repo-add --type helm-chart --description "Repository for Powerdns helm Chart" osm-helm https://gatici.github.io/helm-repo/
```

## Onboarding and instantiation

```bash
VNF_NAME=powerdns
KDU_NAME=powerdns
# Define the NS name
NS_NAME=<ns name>
# Define the vim_account
VIM_ACCOUNT=<vim_account_name|vim_account_id>
```

```bash
osm nfpkg-create powerdns_knf
osm nspkg-create powerdns_ns
OP_ID=`osm ns-create --ns_name $NS_NAME --nsd_name powerdns_ns --vim_account $VIM_ACCOUNT --config "{vld: [ {name: mgmtnet, vim-network-name: osm-ext}]}"`
# Check operation status
osm ns-op-show $OP_ID
osm ns-list
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
DNS_IP=`osm vnf-show $VNF_ID --literal | yq e '.kdur[0].services[] | select(.name == "osm-helm-powerdns*tcp") | .external_ip' | sed 's/- //g'`
RECORD=<domain><zone> 
# Sample record: "test.example.org"
dig @$DNS_IP +tcp $RECORD
```

## Test Day2 Actions: delete-domain, delete-zone

```bash
# Delete Domain
OP_ID=`osm ns-action --action_name delete-domain --vnf_name $VNF_NAME --kdu_name $KDU_NAME  --params "{'zone_name': $ZONE, 'subdomain': $DOMAIN}" $NS_NAME`
osm ns-op-show $OP_ID
dig @$DNS_IP +tcp $RECORD
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
