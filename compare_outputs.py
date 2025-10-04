import json
import os

# List of files to compare
files_to_compare = [
    ('jacksonpoemailtemp00157181_epicor.json', 'jacksonpoemailtemp00157181_NEW.json'),
    ('airliquide89609717_epicor.json', 'airliquide89609717_NEW.json'),
    ('lampton00599468_epicor.json', 'lampton00599468_NEW.json'),
    ('IWTS03986860_epicor.json', 'IWTS03986860_NEW.json'),
    ('holston1_final_epicor.json', 'holston1_NEW.json')
]

print('🔍 COMPARING OLD vs NEW OUTPUTS')
print('=' * 60)

for old_file, new_file in files_to_compare:
    print(f'\n📋 Comparing {old_file} vs {new_file}:')
    
    try:
        # Load both files
        with open(f'processed/epicor_batch/{old_file}', 'r') as f:
            old_data = json.load(f)
        with open(f'processed/epicor_batch/{new_file}', 'r') as f:
            new_data = json.load(f)
        
        # Compare key fields
        differences = []
        
        # Check billing address
        old_billing = old_data.get('OTSName', '') + ' ' + old_data.get('OTSAddress1', '')
        new_billing = new_data.get('OTSName', '') + ' ' + new_data.get('OTSAddress1', '')
        if old_billing.strip() != new_billing.strip():
            differences.append(f'Billing: OLD="{old_billing.strip()}" NEW="{new_billing.strip()}"')
        
        # Check shipping address  
        old_shipping = old_data.get('OTSName', '') + ' ' + old_data.get('OTSAddress1', '')
        new_shipping = new_data.get('OTSName', '') + ' ' + new_data.get('OTSAddress1', '')
        if old_shipping.strip() != new_shipping.strip():
            differences.append(f'Shipping: OLD="{old_shipping.strip()}" NEW="{new_shipping.strip()}"')
        
        # Check customer account
        old_cust = old_data.get('CustNum', '')
        new_cust = new_data.get('CustNum', '')
        if old_cust != new_cust:
            differences.append(f'Customer: OLD="{old_cust}" NEW="{new_cust}"')
        
        # Check company name
        old_company = old_data.get('Company', '')
        new_company = new_data.get('Company', '')
        if old_company != new_company:
            differences.append(f'Company: OLD="{old_company}" NEW="{new_company}"')
        
        if differences:
            print('   🔄 DIFFERENCES FOUND:')
            for diff in differences:
                print(f'     • {diff}')
        else:
            print('   ✅ NO DIFFERENCES - Identical outputs')
            
    except Exception as e:
        print(f'   ❌ Error comparing: {str(e)}')

print('\n✅ Comparison complete!')
