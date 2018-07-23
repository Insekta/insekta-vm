#!/usr/bin/env bash

# Excerpt from the OpenVPN manpage:
# [1] operation -- "add", "update", or "delete" based on whether or not  the  address  is
# being added to, modified, or deleted from OpenVPN's internal routing table.
# [2]  address  --  The  address being learned or unlearned.  This can be an IPv4 address
# such as "198.162.10.14", an IPv4 subnet such as "198.162.10.0/24", or an  ethernet  MAC
# address (when --dev tap is being used) such as "00:FF:01:02:03:04".
# [3] common name -- The common name on the certificate associated with the client linked
# to this address.  Only present for "add" or "update" operations, not "delete".
#
# On "add" or "update" methods, if the script returns a failure code (non-zero),  OpenVPN
# will reject the address and will not modify its internal routing table.

OPERATION=$1
ADDRESS=$2
USERNAME=$3

APIURL=http://localhost:8000/api/1.0/
CURLOPTS="--basic --netrc-file api.netrc --fail --silent"

if [ $OPERATION == "add" -o $OPERATION == "update" ]
then
    curl $CURLOPTS --data-urlencode "username=$USERNAME" --data-urlencode "ip_address=$ADDRESS" "${APIURL}vpn/assign" > /dev/null
elif [ $OPERATION == "delete" ]
then
    curl $CURLOPTS --data-urlencode "ip_address=$ADDRESS" "${APIURL}vpn/unassign" > /dev/null
else
    echo "Invalid operation."
    exit 1
fi

exit 0
