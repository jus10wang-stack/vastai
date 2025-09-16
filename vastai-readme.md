# Vast.ai Instance Creation and Access Guide

## Creating an Instance

### Option 1: Using Template Hash ID (Recommended)
1. Get the template hash ID from your template
2. Create instance using the hash ID through the web console or CLI
3. Wait for instance to provision and start

### Option 2: Using API (Currently Not Working)
**Note**: Creating instances from templates via API does not currently work properly. Use the template hash ID method instead.

## Accessing Your Instance

Once your instance is running:

1. **Open the instance** through the Vast.ai console
2. **Login credentials**:
   - Username: `vastai`
   - Password: `{token}` (your actual Vast.ai URL token)

## Important Notes

- The provisioning script will automatically download and set up all required models
- First boot may take 10-20 minutes depending on model sizes
- Check the instance logs to monitor provisioning progress
- Jupyter will be available on port 8080
- ComfyUI will be available on port 8188

## Troubleshooting

- If login fails, ensure you're using your actual token as the password, not the literal string "{token}"
- If provisioning seems stuck, check instance logs for download progress
- For faster downloads, use provision_test_2.sh which uses aria2c for parallel downloading