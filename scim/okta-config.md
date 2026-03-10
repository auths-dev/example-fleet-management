# Okta SCIM Integration

Connect Okta to Auths for automated identity provisioning and deprovisioning.

## Prerequisites

- Okta admin access
- SCIM webhook handler running (see `docker compose up`)
- SCIM bearer token configured in `.env`

## Setup Steps

### 1. Create a SCIM Application in Okta

1. Go to **Applications** > **Create App Integration**
2. Select **SCIM 2.0 Test App (Header Auth)**
3. Name it "Auths Identity Provisioning"

### 2. Configure SCIM Connection

In the app's **Provisioning** tab:

| Setting | Value |
|---------|-------|
| SCIM connector base URL | `https://your-scim-handler.example.com/scim/v2` |
| Unique identifier field | `userName` |
| Authentication Mode | HTTP Header |
| Authorization | `Bearer <your-scim-token>` |

### 3. Enable Provisioning Features

Under **To App**:
- [x] Create Users
- [x] Deactivate Users

### 4. Assign Users

1. Go to the **Assignments** tab
2. Assign individual users or groups
3. Okta will automatically call `POST /scim/v2/Users` for each assigned user

### 5. Test

1. Assign a test user in Okta
2. Check the webhook handler logs: `docker compose logs webhook-handler`
3. Verify the user's key was added: `cat .auths/allowed_signers`

## Deprovisioning

When a user is unassigned or deactivated in Okta:
1. Okta sends `DELETE /scim/v2/Users/<id>`
2. The webhook handler removes their key from `allowed_signers`

## Troubleshooting

- **401 Unauthorized**: Check that the bearer token in Okta matches `SCIM_BEARER_TOKEN` in `.env`
- **Connection timeout**: Ensure the webhook handler is publicly accessible (or use a tunnel like ngrok for testing)
- **User not provisioned**: Check that the user has Ed25519 SSH keys on GitHub
