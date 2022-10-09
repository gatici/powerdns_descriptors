# PowerDNS NS

Descriptors that installs a PowerDNS chart from "https://gatici.github.io/helm-repo/" repo.

There is one VNF (powerdns_knf) with only one KDU.

There is one NS that connects the VNF to a mgmt network

## Onboarding and instantiation
NS_NAME=powerdns_ns
VNF_NAME=powerdns
KDU_NAME=powerdns_kdu
# Please define the vim_account
VIM_ACCOUNT=<vim_account_name|vim_account_id>

```bash
osm nfpkg-create powerdns_knf.tar.gz
osm nspkg-create powerdns_ns.tar.gz
osm ns-create --ns_name powerdns --nsd_name powerdns_ns --vim_account $VIM_ACCOUNT --config '{vld: [ {name: mgmtnet, vim-network-name: osm-ext}]}' 
```

## Test Day2 Actions: add-zone, add-domain

```bash
VNF_ID=`osm vnf-list --ns $NS_NAME | grep powerdns | awk '{print $2}'`
WEBSERVER_SERVICE_NAME=`osm vnf-show $VNF_ID --literal | yq e '.kdur[0].services[] | select(.name == "gatici-repo-powerdns*webserver") | .name'`
# Add Zone Action
ZONE=<zone> 
# Sample: "example.org."
OP_ID=osm ns-action --action_name add-zone --vnf_name $VNF_NAME --kdu_name $KDU_NAME --params '{"zone_name":$ZONE, "service_name": $WEBSERVER_SERVICE_NAME' $NS_NAME 
# Check operation status
osm ns-op-show ${OP_ID}
# Add Domain Action
DOMAIN=<domain> 
# Smaple: "test."
IP=<ip>
# Sample: 192.168.2.32
osm ns-action --action_name add-domain --vnf_name $VNF_NAME --kdu_name $KDU_NAME  --params '{"zone_name":$ZONE, "subdomain": $DOMAIN, "ip": $IP, "service_name": $WEBSERVER_SERVICE_NAME}' $NS_NAME
```

## Testing PowerDNS server

```bash
DNS_IP=`osm vnf-show $VNF_ID --literal | yq e '.kdur[0].services[] | select(.name == "gatici-repo-powerdns*tcp") | .external_ip' | sed 's/- //g'`
RECORD=<domain><zone> 
# Smaple: "test.example.org"
dig @$DNS_IP +tcp $RECORD
```

## Test Day2 Actions: delete-domain, delete-zone

```bash
# Delete Domain
osm ns-action  --action_name delete-domain --vnf_name $VNF_NAME --kdu_name $KDU_NAME  --params '{"zone_name":$ZONE, "subdomain": $DOMAIN, "service_name": $WEBSERVER_SERVICE_NAME}' $NS_NAME
dig @$DNS_IP +tcp $RECORD
# Delete Zone
osm ns-action --action_name delete-zone --vnf_name $KDU_NAME --kdu_name $KDU_NAME  --params '{"zone_name":$ZONE, "service_name": $WEBSERVER_SERVICE_NAME}' $NS_NAME
```

## Upgrade Operation: Scale Out

```bash
OP_ID=osm ns-action --action_name upgrade --vnf_name $VNF_NAME  --kdu_name $KDU_NAME --params '{"replicaCount":"3",}' $NS_NAME
osm ns-op-show $OP_ID --literal | yq .operationState
osm vnf-show $VNF_ID --kdu powerdns | yq .config.replicaCount
```


## Rollback Operation: Scale In

```bash
OP_ID=osm ns-action --action_name rollback --vnf_name $VNF_NAME --kdu_name $KDU_NAME $NS_NAME
osm ns-op-show $OP_ID --literal | yq .operationState
osm vnf-show $VNF_ID --kdu $KDU_NAME | yq .config.replicaCount 
```
