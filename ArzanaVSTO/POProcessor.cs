using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Web;
using Outlook = Microsoft.Office.Interop.Outlook;

namespace ArzanaVSTO
{
    public class POProcessor
    {
        private readonly string flaskServerUrl = "http://127.0.0.1:5000";
        private readonly HttpClient httpClient;

        public POProcessor()
        {
            httpClient = new HttpClient();
            httpClient.Timeout = TimeSpan.FromMinutes(5); // 5 minute timeout for processing
        }

        public async Task<ProcessingResult> ProcessEmailAsync(Outlook.MailItem mailItem)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine("Arzana VSTO: Starting email processing...");

                // Check if there are PDF attachments to process
                var pdfAttachment = GetFirstPDFAttachment(mailItem);
                
                if (pdfAttachment != null)
                {
                    System.Diagnostics.Debug.WriteLine($"Arzana VSTO: Processing PDF attachment: {pdfAttachment.FileName}");
                    return await ProcessPDFAttachment(mailItem, pdfAttachment);
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine("Arzana VSTO: No PDF attachments found, processing email body");
                    return await ProcessEmailBody(mailItem);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: ProcessEmailAsync error - {ex.Message}");
                return new ProcessingResult
                {
                    Status = "error",
                    ErrorMessage = ex.Message,
                    CustomerMatched = false,
                    PartsMapped = 0,
                    PartsTotal = 0,
                    ConfidenceScore = 0
                };
            }
        }

        private Outlook.Attachment GetFirstPDFAttachment(Outlook.MailItem mailItem)
        {
            try
            {
                if (mailItem.Attachments == null) return null;

                for (int i = 1; i <= mailItem.Attachments.Count; i++)
                {
                    var attachment = mailItem.Attachments[i];
                    if (attachment.FileName.ToLower().EndsWith(".pdf"))
                    {
                        return attachment;
                    }
                }
                return null;
            }
            catch
            {
                return null;
            }
        }

        private async Task<ProcessingResult> ProcessPDFAttachment(Outlook.MailItem mailItem, Outlook.Attachment attachment)
        {
            try
            {
                // Save attachment to temp file
                string tempPath = Path.GetTempFileName();
                attachment.SaveAsFile(tempPath);

                try
                {
                    // Read the file and send to Flask server
                    byte[] fileBytes = File.ReadAllBytes(tempPath);
                    var result = await SendToFlaskServer(fileBytes, attachment.FileName);
                    return result;
                }
                finally
                {
                    // Clean up temp file
                    if (File.Exists(tempPath))
                        File.Delete(tempPath);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: ProcessPDFAttachment error - {ex.Message}");
                return new ProcessingResult
                {
                    Status = "error",
                    ErrorMessage = ex.Message,
                    CustomerMatched = false,
                    PartsMapped = 0,
                    PartsTotal = 0,
                    ConfidenceScore = 0
                };
            }
        }

        private async Task<ProcessingResult> ProcessEmailBody(Outlook.MailItem mailItem)
        {
            try
            {
                // Get email body text
                string bodyText = GetEmailBodyText(mailItem);
                
                // Create a text file from the email body
                byte[] bodyBytes = Encoding.UTF8.GetBytes(bodyText);
                var result = await SendToFlaskServer(bodyBytes, "email_content.txt");
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: ProcessEmailBody error - {ex.Message}");
                return new ProcessingResult
                {
                    Status = "error",
                    ErrorMessage = ex.Message,
                    CustomerMatched = false,
                    PartsMapped = 0,
                    PartsTotal = 0,
                    ConfidenceScore = 0
                };
            }
        }

        private string GetEmailBodyText(Outlook.MailItem mailItem)
        {
            try
            {
                // Try to get plain text body first
                if (!string.IsNullOrEmpty(mailItem.Body))
                {
                    return mailItem.Body;
                }
                
                // If no plain text, try to extract from HTML
                if (!string.IsNullOrEmpty(mailItem.HTMLBody))
                {
                    return System.Text.RegularExpressions.Regex.Replace(mailItem.HTMLBody, "<.*?>", " ");
                }
                
                return "";
            }
            catch
            {
                return "";
            }
        }

        private async Task<ProcessingResult> SendToFlaskServer(byte[] fileBytes, string fileName)
        {
            try
            {
                using (var formData = new MultipartFormDataContent())
                {
                    var fileContent = new ByteArrayContent(fileBytes);
                    fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/octet-stream");
                    formData.Add(fileContent, "file", fileName);

                    System.Diagnostics.Debug.WriteLine($"Arzana VSTO: Sending to Flask server: {flaskServerUrl}/upload");

                    var response = await httpClient.PostAsync($"{flaskServerUrl}/upload", formData);
                    
                    if (response.IsSuccessStatusCode)
                    {
                        string jsonResponse = await response.Content.ReadAsStringAsync();
                        return ParseFlaskResponse(jsonResponse);
                    }
                    else
                    {
                        System.Diagnostics.Debug.WriteLine($"Arzana VSTO: Flask server error - {response.StatusCode}");
                        return new ProcessingResult
                        {
                            Status = "error",
                            ErrorMessage = $"Flask server error: {response.StatusCode}",
                            CustomerMatched = false,
                            PartsMapped = 0,
                            PartsTotal = 0,
                            ConfidenceScore = 0
                        };
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: SendToFlaskServer error - {ex.Message}");
                return new ProcessingResult
                {
                    Status = "error",
                    ErrorMessage = ex.Message,
                    CustomerMatched = false,
                    PartsMapped = 0,
                    PartsTotal = 0,
                    ConfidenceScore = 0
                };
            }
        }

        private ProcessingResult ParseFlaskResponse(string jsonResponse)
        {
            try
            {
                // Simple JSON parsing - in a real implementation, you'd use Newtonsoft.Json
                // For now, we'll create a basic result
                var result = new ProcessingResult();
                
                if (jsonResponse.Contains("\"success\": true"))
                {
                    result.Status = "success";
                    result.CustomerMatched = jsonResponse.Contains("\"customer_match_status\": \"matched\"");
                    
                    // Extract parts information (simplified parsing)
                    if (jsonResponse.Contains("\"parts_mapped\""))
                    {
                        // This would need proper JSON parsing in a real implementation
                        result.PartsMapped = 1; // Placeholder
                        result.PartsTotal = 1; // Placeholder
                    }
                    
                    result.ConfidenceScore = 85; // Placeholder
                }
                else
                {
                    result.Status = "error";
                    result.ErrorMessage = "Processing failed";
                }
                
                return result;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: ParseFlaskResponse error - {ex.Message}");
                return new ProcessingResult
                {
                    Status = "error",
                    ErrorMessage = ex.Message,
                    CustomerMatched = false,
                    PartsMapped = 0,
                    PartsTotal = 0,
                    ConfidenceScore = 0
                };
            }
        }

        public void Dispose()
        {
            httpClient?.Dispose();
        }
    }

    public class ProcessingResult
    {
        public string Status { get; set; } // "success", "error", "missing_info"
        public string ErrorMessage { get; set; }
        public bool CustomerMatched { get; set; }
        public int PartsMapped { get; set; }
        public int PartsTotal { get; set; }
        public int ConfidenceScore { get; set; }
    }
}
