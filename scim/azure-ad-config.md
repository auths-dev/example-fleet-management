# Azure AD SCIM Integration

Connect Azure Active Directory (Entra ID) to Auths for automated identity provisioning.

## Prerequisites

- Azure AD admin access
- SCIM webhook handler running (see `docker compose up`)
- SCIM bearer token configured in `.env`

## Setup Steps

### 1. Create an Enterprise Application

1. Go to **Azure Portal** > **Enterprise Applications** > **New Application**
2. Select **Create your own application**
3. Name it "Auths Identity Provisioning"
4. Select "Integrate any other application you don't find in the gallery"

### 2. Configure Provisioning

1. Go to the application's **Provisioning** page
2. Set **Provisioning Mode** to **Automatic**
3. Under **Admin Credentials**:

| Setting | Value |
|---------|-------|
| Tenant URL | `https://your-scim-handler.example.com/scim/v2` |
| Secret Token | `<your-scim-token>` |

4. Click **Test Connection** to verify

### 3. Configure Attribute Mapping

Under **Provisioning** > **Mappings** > **Provision Azure Active Directory Users**:

| Azure AD Attribute | SCIM Attribute |
|-------------------|----------------|
| userPrincipalName | userName |
| displayName | displayName |
| mail | emails[type eq "work"].value |

### 4. Assign Users and Groups

1. Go to **Users and groups**
2. Add users or groups to provision
3. Azure AD will call `POST /scim/v2/Users` for each user

### 5. Start Provisioning

1. Return to **Provisioning**
2. Set **Provisioning Status** to **On**
3. Save

Initial provisioning runs within 40 minutes. Subsequent cycles run every ~40 minutes.

## Deprovisioning

When a user is removed from the application or disabled in Azure AD:
1. Azure AD sends a SCIM update to deactivate the user
2. The webhook handler removes their key from `allowed_signers`

## Troubleshooting

- **Test Connection fails**: Ensure the webhook handler is accessible from Azure. Use a public URL or Azure Private Link.
- **Provisioning stuck**: Check **Provisioning logs** in Azure for error details.
- **Attribute mapping errors**: Ensure `userName` maps to a field that contains the GitHub username or email.
