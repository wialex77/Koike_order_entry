/*
 * Copyright (c) Microsoft Corporation. All rights reserved. Licensed under the MIT license.
 * See LICENSE in the project root for license information.
 */

/* global console, document, Excel, Office, OfficeExtension */

Office.onReady((info) => {
  if (info.host === Office.HostType.Outlook) {
    // Make functions globally accessible
    (window as any).createOrderAcknowledgementDraft = createOrderAcknowledgementDraft;
    (window as any).sendAcknowledgementEmail = sendAcknowledgementEmail;
    
    // Initialize the app when Outlook is ready
    initializeApp();
  }
});

// Functions will be made globally available at the end of the file

let currentEmailData: any = null;
let processedData: any = null;
let currentValidation: any = null;
let currentFileId: number = 0;

// Background processing variables
let autoProcessingEnabled = true;
let processedEmails = new Set<string>();

// Load sample data for debugging
function loadSampleData() {
  console.log('loadSampleData function called!');
  (window as any).loadSampleData = loadSampleData;
  
  // Create sample data based on the nexair example
  const sampleData = {
    company_info: {
      account_number: '781',
      customer_po_number: '11082962',
      po_date: '2025-10-01T13:21:21.395581Z',
      company_name: 'NAK CONSTRUCTION SERVICES LLC',
      billing_company_name: 'NAK CONSTRUCTION SERVICES LLC',
      shipping_address: '140 SOUTH HOLLAND DRIVE, PENDERGRASS, GA 30567',
      shipping_method: 'GROUND',
      shipping_account_number: 'prepaid & add'
    },
    line_items: [
      {
        internal_part_number: 'ZTIP107D73',
        description: 'CUTTING TIP KOIKE #3',
        quantity: '5',
        unit_price: '19.80',
        external_part_number: 'ZTIP107D73',
        mapping_status: 'mapped',
        mapping_confidence: 95
      },
      {
        internal_part_number: 'ZTIP107D74',
        description: 'TIP, CUTTING 107D7 #4 NAT GAS',
        quantity: '5',
        unit_price: '19.80',
        external_part_number: 'ZTIP107D74',
        mapping_status: 'mapped',
        mapping_confidence: 95
      },
      {
        internal_part_number: 'ZTIP107D75',
        description: 'TIP 107D7 #5 HIGH SPEED NATURAL GAS CUTTING TIP',
        quantity: '10',
        unit_price: '18.00',
        external_part_number: 'ZTIP107D75',
        mapping_status: 'mapped',
        mapping_confidence: 95
      }
    ]
  };
  
  // Store the sample data
  processedData = sampleData;
  currentFileId = 0;
  
  // Show the form interface
  displayResults(sampleData, null, null).catch(console.error);
}

// Fallback function for when Flask server is not available
function showFallbackForm() {
  console.log('showFallbackForm function called!');
  (window as any).showFallbackForm = showFallbackForm;
  
  // Get email info for manual entry
  const subject = Office.context.mailbox.item.subject;
  const from = Office.context.mailbox.item.from?.displayName || Office.context.mailbox.item.from?.emailAddress || 'Unknown';
  
  // Create a blank form with email context
  const fallbackData = {
    company_info: {
      account_number: '',
      customer_po_number: '',
      po_date: new Date().toISOString(),
      company_name: '',
      shipping_address: '',
      shipping_method: 'GROUND',
      shipping_account_number: 'prepaid & add'
    },
    line_items: [
      {
        internal_part_number: '',
        description: '',
        quantity: '',
        unit_price: '',
        external_part_number: '',
        mapping_status: 'manual',
        mapping_confidence: 0
      }
    ],
    email_context: {
      subject: subject,
      from: from
    }
  };
  
  // Store the fallback data
  processedData = fallbackData;
  currentFileId = 0;
  
  // Show the form interface
  displayResults(fallbackData, null, null).catch(console.error);
}

async function initializeApp() {
  try {
    // Initialize background processing
    initializeBackgroundProcessing();
    
    // Add event listener for email selection changes
    Office.context.mailbox.addHandlerAsync(
      Office.EventType.ItemChanged,
      onItemChanged
    );
    
    // Get current email data
    await loadEmailData();
    
    // Check if this email has been processed and has tags - if so, show review UI
    const hasProcessedTag = await checkForProcessedEmail();
    
    if (!hasProcessedTag) {
      // Only check for attachments if email hasn't been processed yet
      await checkForPurchaseOrderAttachments();
    }
    
  } catch (error) {
    console.error("Error initializing app:", error);
    showError("Failed to initialize the application: " + error.message);
  }
}

// Event handler for when user switches to a different email
async function onItemChanged() {
  try {
    await loadEmailData();
    const hasProcessedTag = await checkForProcessedEmail();
    
    if (!hasProcessedTag) {
      await checkForPurchaseOrderAttachments();
    }
  } catch (error) {
    console.error("Error handling item change:", error);
  }
}

// Check if email has "Pending Approval" or "Missing Info" tags and load review UI
async function checkForProcessedEmail(): Promise<boolean> {
  return new Promise((resolve) => {
    Office.context.mailbox.item.categories.getAsync((result) => {
      if (result.status === Office.AsyncResultStatus.Succeeded) {
        const categories = result.value;
        
        // Check for our processing tags
        const hasPendingApproval = categories.some(cat => cat.displayName === "Pending Approval");
        const hasMissingInfo = categories.some(cat => cat.displayName === "Missing Info");
        const hasApproved = categories.some(cat => cat.displayName === "Approved");
        
        if (hasPendingApproval || hasMissingInfo || hasApproved) {
          console.log("Email has processing tag, loading review UI...");
          loadReviewUI(categories);
          resolve(true);
        } else {
          resolve(false);
        }
      } else {
        resolve(false);
      }
    });
  });
}

// Load the review UI for a processed email
async function loadReviewUI(categories: any[]) {
  (window as any).loadReviewUI = loadReviewUI;
  try {
    // Check if this email is approved (read-only mode)
    const hasApproved = categories.some(cat => cat.displayName === "Approved");
    
    // Get the email's unique ID and attachment info
    const emailId = Office.context.mailbox.item.conversationId;
    const subject = Office.context.mailbox.item.subject;
    const attachments = Office.context.mailbox.item.attachments;
    
    // Get PDF attachment name if exists
    let attachmentName = '';
    if (attachments && attachments.length > 0) {
      const pdfAttachment = attachments.find(att => att.name.toLowerCase().endsWith('.pdf'));
      if (pdfAttachment) {
        attachmentName = pdfAttachment.name;
      }
    }
    
    // If approved, show read-only form immediately
    if (hasApproved) {
      console.log("Email is approved, showing read-only form...");
      await loadApprovedEmailData(categories);
      return;
    }
    
    // Show loading state
    const uploadSection = document.querySelector('.card-body');
    if (uploadSection) {
      uploadSection.innerHTML = `
        <div class="text-center">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
          <p class="mt-3">Processing email: "${subject}"</p>
          <p class="text-muted small">Attachment: ${attachmentName || 'None'}</p>
          <div class="mt-3">
            <button class="btn btn-sm btn-outline-secondary me-2" id="loadSampleDataBtn">
              <i class="fas fa-flask"></i> Load Sample Data (Debug)
      </button>
            <button class="btn btn-sm btn-outline-primary" id="skipLoadingBtn">
              <i class="fas fa-forward"></i> Skip to Manual Entry
      </button>
    </div>
    </div>
  `;
  
      // Add event listeners for debug buttons
      setTimeout(() => {
        const loadSampleBtn = document.getElementById('loadSampleDataBtn');
        const skipBtn = document.getElementById('skipLoadingBtn');
        
        if (loadSampleBtn) {
          loadSampleBtn.addEventListener('click', loadSampleData);
        }
        
        if (skipBtn) {
          skipBtn.addEventListener('click', showFallbackForm);
        }
      }, 100);
    }

    // Try to get processed data from Flask server
    try {
      const response = await fetch(`https://bx3w2xz6f6.us-east-1.awsapprunner.com/api/get_processed_email?email_id=${encodeURIComponent(emailId)}&subject=${encodeURIComponent(subject)}&attachment_name=${encodeURIComponent(attachmentName)}`, {
        method: 'GET',
      headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success && result.data) {
        // Store the file ID for later use
        currentFileId = result.file_id || 0;
        // Display the actual processed data from this email
        await displayResults(result.data, result.reviewReport, result.validation);
    } else {
        throw new Error(result.message || 'No processed data found');
      }
    } catch (fetchError) {
      console.error('Error fetching from Flask server:', fetchError);
      
      // Show fallback message when Flask server is not available
      const uploadSection = document.querySelector('.card-body');
      if (uploadSection) {
        uploadSection.innerHTML = `
          <div class="alert alert-warning">
            <h5><i class="fas fa-exclamation-triangle"></i> Flask Server Connection Error</h5>
            <p><strong>Error:</strong> ${fetchError.message}</p>
            <p>Could not connect to the processing server. This might be because:</p>
            <ul>
              <li>Flask server is not running on port 5000</li>
              <li>Email hasn't been processed yet</li>
              <li>Network connectivity issues</li>
            </ul>
            <div class="mt-3">
              <button class="btn btn-primary me-2" onclick="location.reload()">
                <i class="fas fa-sync"></i> Retry
              </button>
              <button class="btn btn-outline-secondary" onclick="showFallbackForm()">
                <i class="fas fa-edit"></i> Manual Entry
              </button>
      </div>
    </div>
  `;
      }
      }
    } catch (error) {
    console.error("Error loading review UI:", error);
    showError("Failed to load email data: " + error.message);
  }
}

// Load approved email data in read-only mode
async function loadApprovedEmailData(categories: any[]) {
  try {
    // Get the email's unique ID and attachment info
    const emailId = Office.context.mailbox.item.conversationId;
    const subject = Office.context.mailbox.item.subject;
      const attachments = Office.context.mailbox.item.attachments;

    // Get PDF attachment name if exists
      let attachmentName = '';
      if (attachments && attachments.length > 0) {
        const pdfAttachment = attachments.find(att => att.name.toLowerCase().endsWith('.pdf'));
        if (pdfAttachment) {
          attachmentName = pdfAttachment.name;
        }
      }
      
    // Try to get processed data from Flask server
    try {
      const response = await fetch(`https://bx3w2xz6f6.us-east-1.awsapprunner.com/api/get_processed_email?email_id=${encodeURIComponent(emailId)}&subject=${encodeURIComponent(subject)}&attachment_name=${encodeURIComponent(attachmentName)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success && result.data) {
        // Store the file ID for later use
        currentFileId = result.file_id || 0;
        // Display the approved data in read-only mode
        await displayApprovedResults(result.data, result.reviewReport, result.validation);
      } else {
        throw new Error(result.message || 'No processed data found');
      }
    } catch (fetchError) {
      console.error('Error fetching approved email data:', fetchError);
      showError('Could not load approved order data: ' + fetchError.message);
      }
    } catch (error) {
    console.error("Error loading approved email data:", error);
    showError("Failed to load approved email data: " + error.message);
  }
}

// Display approved results in read-only mode
async function displayApprovedResults(data: any, reviewReport: any, validation: any) {
  // Store the processed data
  processedData = data;
  currentValidation = validation;
  
  // Convert Epicor format to form format if needed
  const formData = await convertToFormFormat(data);
  
  // Get current timestamp for display
  const enteredTimestamp = new Date().toLocaleString();
  
  // Show the read-only Epicor order form
  const uploadSection = document.querySelector('.card-body');
  if (uploadSection) {
    uploadSection.innerHTML = `
      <div id="formView">
        <div class="card" id="epicorFormCard">
          <div class="card-header bg-success text-white">
            <h5 class="mb-0"><i class="fas fa-check-circle"></i> Entered ${enteredTimestamp}</h5>
          </div>
          <div class="card-body">
            <!-- Order Header Section -->
            <div class="mb-4">
              <h6 class="border-bottom pb-2"><i class="fas fa-heading"></i> Order Header</h6>
              <div class="row">
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Customer Number *</label>
                    <input type="text" class="form-control" id="custNum" value="${formData.custNum}" readonly>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Customer Name</label>
                    <input type="text" class="form-control" id="customerName" value="${formData.customerName || ''}" readonly>
                    <small class="form-text text-muted">Extracted from account number</small>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">PO Number *</label>
                    <input type="text" class="form-control" id="poNum" value="${formData.poNum}" readonly>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Order Date</label>
                    <input type="datetime-local" class="form-control" id="orderDate" value="${formData.orderDate}" readonly>
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Ship Via Code</label>
                    <select class="form-select" id="shipViaCode" disabled>
                      <option value="INVO" ${formData.shipViaCode === 'INVO' ? 'selected' : ''}>INVO</option>
                      <option value="UPS" ${formData.shipViaCode === 'UPS' ? 'selected' : ''}>UPS</option>
                      <option value="FEDEX" ${formData.shipViaCode === 'FEDEX' ? 'selected' : ''}>FEDEX</option>
                      <option value="TRUCK" ${formData.shipViaCode === 'TRUCK' ? 'selected' : ''}>TRUCK</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Payment Flag</label>
                    <select class="form-select" id="payFlag" disabled>
                      <option value="SHIP" ${formData.payFlag === 'SHIP' ? 'selected' : ''}>SHIP</option>
                      <option value="PREPAID" ${formData.payFlag === 'PREPAID' ? 'selected' : ''}>PREPAID</option>
                      <option value="COD" ${formData.payFlag === 'COD' ? 'selected' : ''}>COD</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Shipping Method</label>
                    <select class="form-select" id="shippingMethod" disabled>
                      <option value="GROUND" ${formData.shippingMethod === 'GROUND' ? 'selected' : ''}>Ground</option>
                      <option value="2ND_DAY_AIR" ${formData.shippingMethod === '2ND_DAY_AIR' ? 'selected' : ''}>2nd Day Air</option>
                      <option value="NEXT_DAY_AIR" ${formData.shippingMethod === 'NEXT_DAY_AIR' ? 'selected' : ''}>Next Day Air</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Shipping Account Number</label>
                    <input type="text" class="form-control" id="shippingAccountNumber" value="${formData.shippingAccountNumber}" readonly>
                  </div>
                </div>
              </div>
            </div>

            <!-- One-Time Ship Address Section -->
            <div class="mb-4">
              <h6 class="border-bottom pb-2"><i class="fas fa-map-marker-alt"></i> One-Time Ship Address</h6>
              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="useOTS" ${formData.useOTS ? 'checked' : ''} disabled>
                <label class="form-check-label" for="useOTS">Use One-Time Ship Address</label>
              </div>
              <div class="row">
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Company Name *</label>
                    <input type="text" class="form-control" id="otsName" value="${formData.otsName}" readonly>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Address Line 1 *</label>
                    <input type="text" class="form-control" id="otsAddress1" value="${formData.otsAddress1}" readonly>
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">City *</label>
                    <input type="text" class="form-control" id="otsCity" value="${formData.otsCity}" readonly>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">State *</label>
                    <select class="form-select" id="otsState" disabled>
                      <option value="">Select State</option>
                      <option value="AL">AL</option><option value="AK">AK</option><option value="AZ">AZ</option>
                      <option value="AR">AR</option><option value="CA">CA</option><option value="CO">CO</option>
                      <option value="CT">CT</option><option value="DE">DE</option><option value="FL">FL</option>
                      <option value="GA">GA</option><option value="HI">HI</option><option value="ID">ID</option>
                      <option value="IL">IL</option><option value="IN">IN</option><option value="IA">IA</option>
                      <option value="KS">KS</option><option value="KY">KY</option><option value="LA">LA</option>
                      <option value="ME">ME</option><option value="MD">MD</option><option value="MA">MA</option>
                      <option value="MI">MI</option><option value="MN">MN</option><option value="MS">MS</option>
                      <option value="MO">MO</option><option value="MT">MT</option><option value="NE">NE</option>
                      <option value="NV">NV</option><option value="NH">NH</option><option value="NJ">NJ</option>
                      <option value="NM">NM</option><option value="NY">NY</option><option value="NC">NC</option>
                      <option value="ND">ND</option><option value="OH">OH</option><option value="OK">OK</option>
                      <option value="OR">OR</option><option value="PA">PA</option><option value="RI">RI</option>
                      <option value="SC">SC</option><option value="SD">SD</option><option value="TN">TN</option>
                      <option value="TX">TX</option><option value="UT">UT</option><option value="VT">VT</option>
                      <option value="VA">VA</option><option value="WA">WA</option><option value="WV">WV</option>
                      <option value="WI">WI</option><option value="WY">WY</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">ZIP Code *</label>
                    <input type="text" class="form-control" id="otsZip" value="${formData.otsZip}" readonly>
                  </div>
                </div>
              </div>
            </div>

            <!-- Line Items Section -->
            <div class="mb-4">
              <h6 class="border-bottom pb-2"><i class="fas fa-list"></i> Line Items</h6>
              <div id="lineItemsContainer">
                ${generateReadOnlyLineItemsHtml(formData.lineItems)}
              </div>
            </div>

            <!-- Read-only notice -->
            <div class="alert alert-info">
              <i class="fas fa-info-circle"></i> This order has been entered and cannot be modified.
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Set the state dropdown value
    const stateField = document.getElementById('otsState') as HTMLSelectElement;
    if (stateField) {
      stateField.value = formData.otsState;
    }
  }
}

// Generate read-only line items HTML
function generateReadOnlyLineItemsHtml(lineItems: any[]): string {
  if (!lineItems || lineItems.length === 0) {
    return '<p class="text-muted small">No line items found</p>';
  }
  
  return lineItems.map((item, index) => `
    <div class="line-item-card" data-index="${index}">
      <div class="row">
        <div class="col-md-4">
          <div class="mb-2">
            <label class="form-label">Part Number *</label>
            <input type="text" class="form-control" id="partNum_${index}" value="${item.internal_part_number || ''}" readonly>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Qty *</label>
            <input type="number" class="form-control" id="sellingQuantity_${index}" value="${item.quantity || ''}" readonly>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Price *</label>
            <input type="number" class="form-control" id="docUnitPrice_${index}" value="${item.unit_price || ''}" readonly>
          </div>
        </div>
        <div class="col-md-2">
          <div class="mb-2">
            <label class="form-label">Total</label>
            <input type="text" class="form-control" id="lineTotal_${index}" value="${((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0)).toFixed(2)}" readonly>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <div class="mb-2">
            <label class="form-label">Description</label>
            <input type="text" class="form-control" id="lineDesc_${index}" value="${item.description || ''}" readonly>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <small class="text-muted">
            <strong>Ext:</strong> ${item.external_part_number || 'N/A'} | 
            <strong>Status:</strong> <span class="badge bg-success">Approved</span> | 
            <strong>Conf:</strong> ${(item.mapping_confidence || 0).toFixed(1)}%
          </small>
        </div>
      </div>
    </div>
  `).join('');
}

// Error handling function
function showError(message: string) {
  (window as any).showError = showError;
  const uploadSection = document.querySelector('.card-body');
  if (uploadSection) {
    uploadSection.innerHTML = `
      <div class="alert alert-danger">
        <h5><i class="fas fa-exclamation-triangle"></i> Error</h5>
        <p>${message}</p>
      </div>
    `;
  }
}

// Missing functions that are referenced in the code
async function displayResults(data: any, reviewReport: any, validation: any) {
  // Store the processed data for form binding
  processedData = data;
  currentValidation = validation;
  
  // Convert Epicor format to form format if needed
  const formData = await convertToFormFormat(data);
  
  // Show the actual Epicor order form
  const uploadSection = document.querySelector('.card-body');
  if (uploadSection) {
    uploadSection.innerHTML = `
      <div id="formView">
        <div class="card" id="epicorFormCard">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-file-invoice"></i> Epicor Order Form</h5>
          </div>
          <div class="card-body">
            <!-- Order Header Section -->
            <div class="mb-4">
              <h6 class="border-bottom pb-2"><i class="fas fa-heading"></i> Order Header</h6>
              <div class="row">
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Customer Number *</label>
                    <input type="text" class="form-control" id="custNum" value="${formData.custNum}" required>
                    <div class="field-error" id="custNum_error" style="display: none;"></div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Customer Name</label>
                    <input type="text" class="form-control" id="customerName" value="${formData.customerName || ''}" readonly>
                    <small class="form-text text-muted">Extracted from bill-to address</small>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">PO Number *</label>
                    <input type="text" class="form-control" id="poNum" value="${formData.poNum}" required>
                    <div class="field-error" id="poNum_error" style="display: none;"></div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Order Date</label>
                    <input type="datetime-local" class="form-control" id="orderDate" value="${formData.orderDate}">
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Ship Via Code</label>
                    <select class="form-select" id="shipViaCode">
                      <option value="INVO" ${formData.shipViaCode === 'INVO' ? 'selected' : ''}>INVO</option>
                      <option value="UPS" ${formData.shipViaCode === 'UPS' ? 'selected' : ''}>UPS</option>
                      <option value="FEDEX" ${formData.shipViaCode === 'FEDEX' ? 'selected' : ''}>FEDEX</option>
                      <option value="TRUCK" ${formData.shipViaCode === 'TRUCK' ? 'selected' : ''}>TRUCK</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Payment Flag</label>
                    <select class="form-select" id="payFlag">
                      <option value="SHIP" ${formData.payFlag === 'SHIP' ? 'selected' : ''}>SHIP</option>
                      <option value="PREPAID" ${formData.payFlag === 'PREPAID' ? 'selected' : ''}>PREPAID</option>
                      <option value="COD" ${formData.payFlag === 'COD' ? 'selected' : ''}>COD</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Shipping Method</label>
                    <select class="form-select" id="shippingMethod">
                      <option value="GROUND" ${formData.shippingMethod === 'GROUND' ? 'selected' : ''}>Ground</option>
                      <option value="2ND_DAY_AIR" ${formData.shippingMethod === '2ND_DAY_AIR' ? 'selected' : ''}>2nd Day Air</option>
                      <option value="NEXT_DAY_AIR" ${formData.shippingMethod === 'NEXT_DAY_AIR' ? 'selected' : ''}>Next Day Air</option>
                    </select>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Shipping Account Number</label>
                    <input type="text" class="form-control" id="shippingAccountNumber" value="${formData.shippingAccountNumber}">
                  </div>
                </div>
              </div>
            </div>

            <!-- One-Time Ship Address Section -->
            <div class="mb-4">
              <h6 class="border-bottom pb-2"><i class="fas fa-map-marker-alt"></i> One-Time Ship Address</h6>
              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="useOTS" ${formData.useOTS ? 'checked' : ''}>
                <label class="form-check-label" for="useOTS">Use One-Time Ship Address</label>
              </div>
              <div class="row">
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">Company Name *</label>
                    <input type="text" class="form-control" id="otsName" value="${formData.otsName}" required>
                    <div class="field-error" id="otsName_error" style="display: none;"></div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Address Line 1 *</label>
                    <input type="text" class="form-control" id="otsAddress1" value="${formData.otsAddress1}" required>
                    <div class="field-error" id="otsAddress1_error" style="display: none;"></div>
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="mb-3">
                    <label class="form-label">City *</label>
                    <input type="text" class="form-control" id="otsCity" value="${formData.otsCity}" required>
                    <div class="field-error" id="otsCity_error" style="display: none;"></div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">State *</label>
                    <select class="form-select" id="otsState" required>
                      <option value="">Select State</option>
                      <option value="AL">AL</option><option value="AK">AK</option><option value="AZ">AZ</option>
                      <option value="AR">AR</option><option value="CA">CA</option><option value="CO">CO</option>
                      <option value="CT">CT</option><option value="DE">DE</option><option value="FL">FL</option>
                      <option value="GA">GA</option><option value="HI">HI</option><option value="ID">ID</option>
                      <option value="IL">IL</option><option value="IN">IN</option><option value="IA">IA</option>
                      <option value="KS">KS</option><option value="KY">KY</option><option value="LA">LA</option>
                      <option value="ME">ME</option><option value="MD">MD</option><option value="MA">MA</option>
                      <option value="MI">MI</option><option value="MN">MN</option><option value="MS">MS</option>
                      <option value="MO">MO</option><option value="MT">MT</option><option value="NE">NE</option>
                      <option value="NV">NV</option><option value="NH">NH</option><option value="NJ">NJ</option>
                      <option value="NM">NM</option><option value="NY">NY</option><option value="NC">NC</option>
                      <option value="ND">ND</option><option value="OH">OH</option><option value="OK">OK</option>
                      <option value="OR">OR</option><option value="PA">PA</option><option value="RI">RI</option>
                      <option value="SC">SC</option><option value="SD">SD</option><option value="TN">TN</option>
                      <option value="TX">TX</option><option value="UT">UT</option><option value="VT">VT</option>
                      <option value="VA">VA</option><option value="WA">WA</option><option value="WV">WV</option>
                      <option value="WI">WI</option><option value="WY">WY</option>
                    </select>
                    <div class="field-error" id="otsState_error" style="display: none;"></div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">ZIP Code *</label>
                    <input type="text" class="form-control" id="otsZip" value="${formData.otsZip}" required>
                    <div class="field-error" id="otsZip_error" style="display: none;"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Line Items Section -->
            <div class="mb-4">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0 border-bottom pb-2"><i class="fas fa-list"></i> Line Items</h6>
                <button type="button" class="btn btn-sm btn-outline-primary" id="addLineItem">
                  <i class="fas fa-plus"></i> Add Item
        </button>
      </div>
              <div id="lineItemsContainer">
                ${generateLineItemsHtml(formData.lineItems)}
    </div>
            </div>

            <!-- Action Buttons -->
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-primary" id="saveFormBtn">
                <i class="fas fa-save"></i> Save & Enter Order
              </button>
              <button type="button" class="btn btn-outline-secondary" id="resetFormBtn">
                <i class="fas fa-undo"></i> Reset
        </button>
      </div>
    </div>
      </div>
    </div>
  `;
    
    // Initialize form event listeners
    initializeFormEventListeners();
    
    // Set the state dropdown value
    const stateField = document.getElementById('otsState') as HTMLSelectElement;
    if (stateField) {
      stateField.value = formData.otsState;
    }
    
    // Run initial validation to highlight MISSING fields and set button state
    setTimeout(() => {
      validateForm();
    }, 100);
  }
}

// Save updated data back to Flask server
async function saveUpdatedDataToServer(updatedData: any) {
  try {
    const emailId = Office.context.mailbox.item.itemId;
    const subject = Office.context.mailbox.item.subject;
    const attachmentName = currentFileId ? `attachment_${currentFileId}` : 'unknown';
    
    const response = await fetch('https://bx3w2xz6f6.us-east-1.awsapprunner.com/api/save_updated_data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email_id: emailId,
        subject: subject,
        attachment_name: attachmentName,
        updated_data: updatedData
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('Data saved to server:', result);
    
  } catch (error) {
    console.error('Error saving updated data to server:', error);
    // Don't show error to user since this is background operation
  }
}

// Convert form data back to Epicor format
function convertFormToEpicor(): any {
  // Get all form field values
  const custNum = (document.getElementById('custNum') as HTMLInputElement)?.value || '';
  const poNum = (document.getElementById('poNum') as HTMLInputElement)?.value || '';
  const orderDate = (document.getElementById('orderDate') as HTMLInputElement)?.value || new Date().toISOString().slice(0, 16);
  const shipViaCode = (document.getElementById('shipViaCode') as HTMLSelectElement)?.value || 'INVO';
  const payFlag = (document.getElementById('payFlag') as HTMLSelectElement)?.value || 'SHIP';
  const shippingMethod = (document.getElementById('shippingMethod') as HTMLSelectElement)?.value || 'GROUND';
  const shippingAccountNumber = (document.getElementById('shippingAccountNumber') as HTMLInputElement)?.value || 'prepaid & add';
  const useOTS = (document.getElementById('useOTS') as HTMLInputElement)?.checked || false;
  const otsName = (document.getElementById('otsName') as HTMLInputElement)?.value || '';
  const otsAddress1 = (document.getElementById('otsAddress1') as HTMLInputElement)?.value || '';
  const otsCity = (document.getElementById('otsCity') as HTMLInputElement)?.value || '';
  const otsState = (document.getElementById('otsState') as HTMLSelectElement)?.value || '';
  const otsZip = (document.getElementById('otsZip') as HTMLInputElement)?.value || '';
  
  // Get line items
  const lineItems = [];
  const lineItemCards = document.querySelectorAll('.line-item-card');
  
  lineItemCards.forEach((card, index) => {
    const partNum = (document.getElementById(`partNum_${index}`) as HTMLInputElement)?.value || '';
    const description = (document.getElementById(`lineDesc_${index}`) as HTMLInputElement)?.value || '';
    const quantity = (document.getElementById(`sellingQuantity_${index}`) as HTMLInputElement)?.value || '';
    const unitPrice = (document.getElementById(`docUnitPrice_${index}`) as HTMLInputElement)?.value || '';
    
    if (partNum || quantity || unitPrice) {
      lineItems.push({
        PartNum: partNum,
        LineDesc: description,
        SellingQuantity: parseFloat(quantity) || 0,
        DocUnitPrice: parseFloat(unitPrice) || 0
      });
    }
  });
  
  // Return in Epicor format
  return {
    ds: {
      OrderHed: [{
        CustNum: custNum,
        PONum: poNum,
        OrderDate: orderDate,
        ShipViaCode: shipViaCode,
        PayFlag: payFlag,
        ShippingMethod: shippingMethod,
        ShippingAccountNumber: shippingAccountNumber,
        UseOTS: useOTS,
        OTSName: otsName,
        OTSAddress1: otsAddress1,
        OTSCity: otsCity,
        OTSState: otsState,
        OTSZip: otsZip
      }],
      OrderDtl: lineItems
    }
  };
}

// Convert Epicor format to form format
// Look up customer name by account number
async function lookupCustomerName(accountNumber: string): Promise<string> {
  try {
    const response = await fetch(`http://localhost:5000/api/get_customer_by_account?account_number=${encodeURIComponent(accountNumber)}`);
    const result = await response.json();
    
    if (result.success && result.customer) {
      return result.customer.company_name;
    }
    
    return '';
  } catch (error) {
    console.error('Error looking up customer:', error);
    return '';
  }
}

async function convertToFormFormat(data: any): Promise<any> {
  // Check if data is in Epicor format (has ds.OrderHed)
  if (data.ds && data.ds.OrderHed && data.ds.OrderHed.length > 0) {
    const orderHed = data.ds.OrderHed[0];
    const orderDtl = data.ds.OrderDtl || [];
    
    // Look up customer name by account number
    const customerName = await lookupCustomerName(orderHed.CustNum || '');
    
    return {
      custNum: orderHed.CustNum || '',
      poNum: orderHed.PONum || '',
      customerName: customerName,
      orderDate: orderHed.OrderDate ? new Date(orderHed.OrderDate).toISOString().slice(0, 16) : new Date().toISOString().slice(0, 16),
      shipViaCode: orderHed.ShipViaCode || 'INVO',
      payFlag: orderHed.PayFlag || 'SHIP',
      shippingMethod: orderHed.ShippingMethod === '2ND_DAY_AIR' ? '2ND_DAY_AIR' : 
                     orderHed.ShippingMethod === 'NEXT_DAY_AIR' ? 'NEXT_DAY_AIR' : 'GROUND',
      shippingAccountNumber: orderHed.ShippingAccountNumber || 'prepaid & add',
      useOTS: orderHed.UseOTS || false,
      otsName: orderHed.OTSName || '',
      otsAddress1: orderHed.OTSAddress1 || '',
      otsCity: orderHed.OTSCity || '',
      otsState: orderHed.OTSState || '',
      otsZip: orderHed.OTSZip || '',
      lineItems: orderDtl.map((item: any) => ({
        internal_part_number: item.PartNum || '',
        description: item.LineDesc || '',
        quantity: item.SellingQuantity || '',
        unit_price: item.DocUnitPrice || '',
        external_part_number: item.PartNum || '',
        mapping_status: 'mapped',
        mapping_confidence: 95
      }))
    };
  }
  
  // If data is already in form format, return as-is
      return {
    custNum: data.company_info?.account_number || '',
    poNum: data.company_info?.customer_po_number || '',
    customerName: await lookupCustomerName(data.company_info?.account_number || ''),
    orderDate: data.company_info?.po_date ? new Date(data.company_info.po_date).toISOString().slice(0, 16) : new Date().toISOString().slice(0, 16),
    shipViaCode: 'INVO',
    payFlag: 'SHIP',
    shippingMethod: data.company_info?.shipping_method || 'GROUND',
    shippingAccountNumber: data.company_info?.shipping_account_number || 'prepaid & add',
    useOTS: true,
    otsName: data.company_info?.company_name || '',
    otsAddress1: data.company_info?.shipping_address || '',
    otsCity: '',
    otsState: '',
    otsZip: '',
    lineItems: data.line_items || []
  };
}

function generateLineItemsHtml(lineItems: any[]): string {
  if (!lineItems || lineItems.length === 0) {
    return '<p class="text-muted small">No line items found</p>';
  }
  
  return lineItems.map((item, index) => `
    <div class="line-item-card" data-index="${index}">
      <div class="position-absolute top-0 end-0">
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeLineItem(${index})">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="row">
        <div class="col-md-4">
          <div class="mb-2">
            <label class="form-label">Part Number *</label>
            <input type="text" class="form-control" id="partNum_${index}" value="${item.internal_part_number || ''}" placeholder="Part #" required>
            <div class="field-error" id="partNum_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Qty *</label>
            <input type="number" class="form-control" id="sellingQuantity_${index}" value="${item.quantity || ''}" placeholder="Qty" required>
            <div class="field-error" id="sellingQuantity_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Price *</label>
            <input type="number" class="form-control" id="docUnitPrice_${index}" value="${item.unit_price || ''}" step="0.01" placeholder="Price" required>
            <div class="field-error" id="docUnitPrice_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="mb-2">
            <label class="form-label">Total</label>
            <input type="text" class="form-control" id="lineTotal_${index}" value="${((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0)).toFixed(2)}" readonly>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <div class="mb-2">
            <label class="form-label">Description</label>
            <input type="text" class="form-control" id="lineDesc_${index}" value="${item.description || ''}" placeholder="Description">
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <small class="text-muted">
            <strong>Ext:</strong> ${item.external_part_number || 'N/A'} | 
            <strong>Status:</strong> <span class="badge bg-${item.mapping_status === 'mapped' ? 'success' : 'warning'}">${item.mapping_status || 'Unknown'}</span> | 
            <strong>Conf:</strong> ${(item.mapping_confidence || 0).toFixed(1)}%
          </small>
        </div>
      </div>
    </div>
  `).join('');
}

function parseShippingAddress(address: string) {
  if (!address) return;
  
  // Parse "140 SOUTH HOLLAND DRIVE, PENDERGRASS, GA 30567"
  const parts = address.split(',');
  if (parts.length >= 2) {
    const cityStateZip = parts[1].trim();
    const cityStateZipParts = cityStateZip.split(' ');
    
    // Set city
    const cityField = document.getElementById('otsCity') as HTMLInputElement;
    if (cityField && cityStateZipParts.length > 0) {
      cityField.value = cityStateZipParts[0];
    }
    
    // Set state
    const stateField = document.getElementById('otsState') as HTMLSelectElement;
    if (stateField && cityStateZipParts.length > 1) {
      stateField.value = cityStateZipParts[1];
    }
    
    // Set ZIP
    const zipField = document.getElementById('otsZip') as HTMLInputElement;
    if (zipField && cityStateZipParts.length > 2) {
      zipField.value = cityStateZipParts[2];
    }
  }
}

function initializeBackgroundProcessing(): void {
  console.log("Arzana: Background processing initialized");
}

async function loadEmailData() {
  // Mock implementation
  return Promise.resolve();
}

async function checkForPurchaseOrderAttachments() {
  // Mock implementation
  return Promise.resolve();
}

// Form event listeners and handlers
function initializeFormEventListeners() {
  // Add line item button
  const addLineItemBtn = document.getElementById('addLineItem');
  addLineItemBtn?.addEventListener('click', addLineItemHandler);
  
  // Save form button
  const saveFormBtn = document.getElementById('saveFormBtn');
  saveFormBtn?.addEventListener('click', saveFormHandler);
  
  // Reset form button
  const resetFormBtn = document.getElementById('resetFormBtn');
  resetFormBtn?.addEventListener('click', resetFormHandler);
  
  // Real-time validation on input change
  const formFields = document.querySelectorAll('#formView input, #formView select');
  formFields.forEach(field => {
    field.addEventListener('blur', validateField);
    field.addEventListener('input', (event) => {
      clearFieldError(event);
      validateForm(); // Update button state in real-time
    });
  });
}

function addLineItemHandler() {
  const container = document.getElementById('lineItemsContainer');
  if (!container) return;
  
  const newIndex = container.children.length;
  const newItem = {
    internal_part_number: '',
    description: '',
    quantity: '',
    unit_price: '',
    external_part_number: '',
    mapping_status: 'manual',
    mapping_confidence: 0
  };
  
  const lineItemHtml = createLineItemHtml(newItem, newIndex);
  container.insertAdjacentHTML('beforeend', lineItemHtml);
  
  // Attach event listeners to new item
  const newCard = container.lastElementChild;
  if (newCard) {
    const inputs = newCard.querySelectorAll('input');
    inputs.forEach(input => {
      input.addEventListener('blur', () => validateLineItem(newIndex));
      input.addEventListener('input', () => clearLineItemError(newIndex));
    });
  }
}

function createLineItemHtml(item: any, index: number): string {
  return `
    <div class="line-item-card" data-index="${index}">
      <div class="position-absolute top-0 end-0">
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeLineItem(${index})">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="row">
        <div class="col-md-4">
          <div class="mb-2">
            <label class="form-label">Part Number *</label>
            <input type="text" class="form-control" id="partNum_${index}" value="${item.internal_part_number || ''}" placeholder="Part #" required>
            <div class="field-error" id="partNum_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Qty *</label>
            <input type="number" class="form-control" id="sellingQuantity_${index}" value="${item.quantity || ''}" placeholder="Qty" required>
            <div class="field-error" id="sellingQuantity_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="mb-2">
            <label class="form-label">Price *</label>
            <input type="number" class="form-control" id="docUnitPrice_${index}" value="${item.unit_price || ''}" step="0.01" placeholder="Price" required>
            <div class="field-error" id="docUnitPrice_error_${index}" style="display: none;"></div>
          </div>
        </div>
        <div class="col-md-2">
          <div class="mb-2">
            <label class="form-label">Total</label>
            <input type="text" class="form-control" id="lineTotal_${index}" value="${((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0)).toFixed(2)}" readonly>
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <div class="mb-2">
            <label class="form-label">Description</label>
            <input type="text" class="form-control" id="lineDesc_${index}" value="${item.description || ''}" placeholder="Description">
          </div>
        </div>
      </div>
      <div class="row">
        <div class="col-12">
          <small class="text-muted">
            <strong>Ext:</strong> ${item.external_part_number || 'N/A'} | 
            <strong>Status:</strong> <span class="badge bg-${item.mapping_status === 'mapped' ? 'success' : 'warning'}">${item.mapping_status || 'Unknown'}</span> | 
            <strong>Conf:</strong> ${(item.mapping_confidence || 0).toFixed(1)}%
          </small>
        </div>
      </div>
    </div>
  `;
}

function saveFormHandler() {
  // First validate the form
  if (!validateForm()) {
    showError('Please complete all required fields and remove any "MISSING" values before saving.');
    return;
  }
  
  // Get form data and convert to Epicor format
  const formData = convertFormToEpicor();
  console.log('Saving updated form data:', formData);
  
  // Update the processed data with manual changes
  processedData = formData;
  
  // Save the updated data back to the Flask server
  saveUpdatedDataToServer(formData);
  
  try {
    console.log('Starting tag update process...');
    
    // First, get current categories to see what's there
    Office.context.mailbox.item.categories.getAsync((getResult) => {
      console.log('Current categories:', getResult);
      
      if (getResult.status === Office.AsyncResultStatus.Succeeded) {
        const currentCategories = getResult.value;
        console.log('Current category names:', currentCategories.map(cat => cat.displayName));
        
        // Remove old tags
        const tagsToRemove = currentCategories
          .filter(cat => ["Pending Approval", "Missing Info", "Approved"].includes(cat.displayName))
          .map(cat => cat.displayName);
        
        console.log('Tags to remove:', tagsToRemove);
        
        if (tagsToRemove.length > 0) {
          Office.context.mailbox.item.categories.removeAsync(tagsToRemove, (removeResult) => {
            console.log('Remove result:', removeResult);
            
            // Add green "Approved" tag
            Office.context.mailbox.item.categories.addAsync(["Approved"], (addResult) => {
              console.log('Add result:', addResult);
              
              if (addResult.status === Office.AsyncResultStatus.Succeeded) {
                showSuccess('Order entered successfully! Email tagged as "Approved"');
                // Create order acknowledgement draft
                createOrderAcknowledgementDraft();
      } else {
                console.error('Add tag failed:', addResult.error);
                showSuccess('Order entered successfully! (Tag update failed: ' + (addResult.error?.message || 'Unknown error') + ')');
                // Still create the draft even if tagging failed
                createOrderAcknowledgementDraft();
              }
            });
          });
        } else {
          // No tags to remove, just add Approved
          Office.context.mailbox.item.categories.addAsync(["Approved"], (addResult) => {
            console.log('Add result (no removal):', addResult);
            
            if (addResult.status === Office.AsyncResultStatus.Succeeded) {
              showSuccess('Order entered successfully! Email tagged as "Approved"');
              // Create order acknowledgement draft
              createOrderAcknowledgementDraft();
      } else {
              console.error('Add tag failed:', addResult.error);
              showSuccess('Order entered successfully! (Tag update failed: ' + (addResult.error?.message || 'Unknown error') + ')');
              // Still create the draft even if tagging failed
              createOrderAcknowledgementDraft();
            }
          });
        }
      } else {
        console.error('Failed to get current categories:', getResult.error);
        showSuccess('Order entered successfully! (Could not read current tags)');
      }
    });
    
  } catch (error) {
    console.error('Error updating email tags:', error);
    showSuccess('Order entered successfully! (Tag update failed: ' + error.message + ')');
  }
}

function resetFormHandler() {
  if (confirm('Are you sure you want to reset the form? All changes will be lost.')) {
    displayResults(processedData, null, null).catch(console.error);
  }
}

function validateForm(): boolean {
  let isValid = true;
  
  // Validate header fields
  const requiredHeaderFields = [
    { id: 'custNum', name: 'Customer Number' },
    { id: 'poNum', name: 'PO Number' },
    { id: 'otsName', name: 'Company Name' },
    { id: 'otsAddress1', name: 'Address Line 1' },
    { id: 'otsCity', name: 'City' },
    { id: 'otsState', name: 'State' },
    { id: 'otsZip', name: 'ZIP Code' }
  ];
  
  requiredHeaderFields.forEach(field => {
    const element = document.getElementById(field.id) as HTMLInputElement | HTMLSelectElement;
    if (element) {
      const value = element.value.trim();
      const hasValue = value && value !== '';
      const hasMissing = value.toUpperCase().includes('MISSING');
      
      if (!hasValue || hasMissing) {
        const errorMessage = hasMissing ? `${field.name} contains "MISSING" and needs to be filled` : `${field.name} is required`;
        markFieldAsInvalid(element, errorMessage);
        isValid = false;
    } else {
        markFieldAsValid(element);
      }
    }
  });
  
  // Validate line items
  const lineItems = document.querySelectorAll('.line-item-card');
  lineItems.forEach((card, index) => {
    if (!validateLineItem(index)) {
      isValid = false;
    }
  });
  
  // Update save button state
  const saveBtn = document.getElementById('saveFormBtn') as HTMLButtonElement;
  if (saveBtn) {
    saveBtn.disabled = !isValid;
    
    // Update button text to show validation status
    if (!isValid) {
      saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Complete Required Fields';
      saveBtn.className = 'btn btn-warning';
      } else {
      saveBtn.innerHTML = '<i class="fas fa-save"></i> Save & Enter Order';
      saveBtn.className = 'btn btn-primary';
    }
  }
  
  return isValid;
}

function validateField(event: Event) {
  const field = event.target as HTMLInputElement;
  const value = field.value.trim();
  
  if (field.required && !value) {
    markFieldAsInvalid(field, 'This field is required');
  } else if (value === 'MISSING' || value.includes('MISSING')) {
    markFieldAsInvalid(field, 'This field contains "MISSING" and needs to be filled');
      } else {
    markFieldAsValid(field);
  }
}

function validateLineItem(index: number): boolean {
  let isValid = true;
  
  const requiredFields = [
    { id: `partNum_${index}`, name: 'Part Number' },
    { id: `sellingQuantity_${index}`, name: 'Quantity' },
    { id: `docUnitPrice_${index}`, name: 'Unit Price' }
  ];
  
  requiredFields.forEach(field => {
    const element = document.getElementById(field.id) as HTMLInputElement;
    if (element) {
      const value = element.value.trim();
      const hasValue = value && value !== '';
      const hasMissing = value.toUpperCase().includes('MISSING');
      
      if (!hasValue || hasMissing) {
        const errorMessage = hasMissing ? `${field.name} contains "MISSING" and needs to be filled` : `${field.name} is required`;
        markFieldAsInvalid(element, errorMessage);
        isValid = false;
      } else {
        markFieldAsValid(element);
      }
    }
  });
  
  return isValid;
}

function markFieldAsInvalid(field: HTMLInputElement | HTMLSelectElement, message: string) {
  field.classList.remove('is-valid');
  field.classList.add('is-invalid');
  
  const errorId = field.id + '_error';
  const errorElement = document.getElementById(errorId);
  if (errorElement) {
    errorElement.textContent = message;
    errorElement.style.display = 'block';
  }
}

function markFieldAsValid(field: HTMLInputElement | HTMLSelectElement) {
  field.classList.remove('is-invalid');
  field.classList.add('is-valid');
  
  const errorId = field.id + '_error';
  const errorElement = document.getElementById(errorId);
  if (errorElement) {
    errorElement.style.display = 'none';
  }
}

function clearFieldError(event: Event) {
  const field = event.target as HTMLInputElement;
  field.classList.remove('is-invalid');
  
  const errorId = field.id + '_error';
  const errorElement = document.getElementById(errorId);
  if (errorElement) {
    errorElement.style.display = 'none';
  }
}

function clearLineItemError(index: number) {
  const fields = [`partNum_${index}`, `sellingQuantity_${index}`, `docUnitPrice_${index}`];
  fields.forEach(fieldId => {
    const field = document.getElementById(fieldId) as HTMLInputElement;
    if (field) {
      field.classList.remove('is-invalid');
      const errorElement = document.getElementById(fieldId + '_error');
      if (errorElement) {
        errorElement.style.display = 'none';
      }
        }
      });
    }
    
function removeLineItem(index: number) {
  if (confirm('Are you sure you want to remove this line item?')) {
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) {
      card.remove();
    }
  }
}

function showSuccess(message: string) {
  const alert = document.createElement('div');
  alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
  alert.style.cssText = 'top: 10px; right: 10px; z-index: 9999; min-width: 300px;';
  alert.innerHTML = `${message}<button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>`;
  document.body.appendChild(alert);
  
  setTimeout(() => alert.remove(), 3000);
}


// Generate acknowledgement email body
function generateAcknowledgementEmailBody(formData: any): string {
  // Get customer name from the original email or use a default
  const originalEmailFrom = Office.context.mailbox.item.from?.displayName || 
                           Office.context.mailbox.item.from?.emailAddress || 
                           'Customer';
  
  // Extract first name from display name
  const firstName = originalEmailFrom.split(' ')[0] || 'Customer';
  
  // Calculate total and format parts
  let totalAmount = 0;
  const partsList = formData.lineItems.map((item: any) => {
    const quantity = parseFloat(item.quantity) || 0;
    const price = parseFloat(item.unit_price) || 0;
    const lineTotal = quantity * price;
    totalAmount += lineTotal;
    
    return `• ${item.internal_part_number}: ${item.quantity} @ $${parseFloat(item.unit_price).toFixed(2)} = $${lineTotal.toFixed(2)}`;
  }).join('\n');
  
  // Calculate delivery date (assuming 3 business days)
  const deliveryDate = new Date();
  deliveryDate.setDate(deliveryDate.getDate() + 3);
  const deliveryDateStr = deliveryDate.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
  
  // Create the acknowledgement email body
  return `Hi ${firstName},

PO${formData.poNum} processed successfully.

Account: ${formData.custNum}
Parts:
${partsList}

Total: $${totalAmount.toFixed(2)}
Delivery: ${deliveryDateStr}

Thanks,
William`;
}

// Create order acknowledgement draft
async function createOrderAcknowledgementDraft() {
  try {
    // Get form data
    const formData = await convertToFormFormat(processedData);
    
    // Generate the email body
    const emailBody = generateAcknowledgementEmailBody(formData);

    // Create a new email draft (we can't modify existing emails in Outlook add-ins)
    Office.context.mailbox.displayNewMessageForm({
      toRecipients: [Office.context.mailbox.item.from?.emailAddress || ''],
      subject: `Order Acknowledgement - PO${formData.poNum}`,
      body: emailBody,
      attachments: []
    });
    
    // Show success message
    showSuccess('Order acknowledgement draft opened! Review and send when ready.');
    
  } catch (error) {
    console.error('Error creating order acknowledgement draft:', error);
    showError('Failed to create order acknowledgement draft: ' + error.message);
  }
}

// Send the acknowledgement email
function sendAcknowledgementEmail() {
  try {
    // Re-create the acknowledgement email draft
    createOrderAcknowledgementDraft();
    
    showSuccess('Acknowledgement draft opened! Review and send when ready.');
    
  } catch (error) {
    console.error('Error opening acknowledgement email:', error);
    showError('Failed to open acknowledgement email: ' + error.message);
  }
}



// Sample data for testing
