# Merge & emit reference

Detail for Step 6 (config write-back) and Step 7 (annotated emit) of the sync skill.

## Step 6 — config.yaml multi-file safety

```yaml
# Before sync (two files):
probes:
  - api-probe/orders/probes.yaml
  - api-probe/products/probes.yaml

# After syncing only orders/probes.yaml — products reference must survive:
probes:
  - api-probe/orders/probes.yaml   # ← synced
  - api-probe/products/probes.yaml # ← untouched
```

Load the full config, update only the synced file's entry, preserve all others. If the config uses a single-path string and the synced file matches, leave it as a string (do not convert to a list).

## Step 7 — Annotated emit example

```yaml
  # SYNC: endpoint updated from /user/${ID}
  - name: "Get User"
    type: rest
    endpoint: "${BASE_URL}/accounts/${USER_ID}"   # ← updated
    method: GET
    validation:                                    # ← preserved
      status: 200
      body:
        present: ["id", "email"]

  # SYNC: body updated — !include reference preserved
  - name: "Create Order"
    type: rest
    endpoint: "${BASE_URL}/orders"
    method: POST
    body: !include includes/create-order.json     # ← preserved
    validation: !include validations/create-order.yaml  # ← preserved

  # SYNC: removed from collection — delete if no longer needed
  - name: "Legacy Endpoint"
    ...

  # SYNC: added — review and add validation
  - name: "New Endpoint"
    ...
    validation:
      status: "2xx"
      # TODO: add body assertions after testing

  # SYNC: new required variable customerId (String!) — add to variables block
  # SYNC: schema added required field data.order.trackingId — update queries/create-order.graphql and validation
  - name: "Create Order (GraphQL)"
    type: graphql
    endpoint: "${BASE_URL}/graphql"
    query: !include queries/create-order.graphql   # ← update this file manually
    variables:
      # TODO: add customerId: "${CUSTOMER_ID}"
    validation: !include validations/create-order.yaml  # ← preserved
```
