using System;
using System.Linq;
using Outlook = Microsoft.Office.Interop.Outlook;

namespace ArzanaVSTO
{
    public class EmailDetector
    {
        private readonly string[] subjectKeywords = {
            "purchase order", "po number", "po#", "order confirmation", "order request",
            "p.o.", "p.o number", "purchase req", "purchase request", "order form",
            "quote", "quotation", "invoice", "billing", "order details",
            "new order", "order placed", "order received", "order summary"
        };

        private readonly string[] bodyKeywords = {
            "purchase order", "po number", "po#", "order number", "order date",
            "bill to", "ship to", "quantity", "unit price", "total amount",
            "part number", "item number", "manufacturer", "supplier", "vendor",
            "order total", "subtotal", "tax", "shipping", "delivery",
            "order confirmation", "order details", "line items", "items ordered",
            "p.o.", "p.o number", "purchase req", "quote number", "quote date",
            "invoice number", "invoice date", "billing address", "shipping address"
        };

        public bool IsPOEmail(Outlook.MailItem mailItem)
        {
            try
            {
                if (mailItem == null) return false;

                string subject = (mailItem.Subject ?? "").ToLower();
                string body = GetEmailBody(mailItem).ToLower();

                // Check subject for PO keywords
                bool subjectMatch = subjectKeywords.Any(keyword => subject.Contains(keyword));

                // Check body for PO keywords
                int bodyMatches = bodyKeywords.Count(keyword => body.Contains(keyword));
                bool bodyMatch = bodyMatches >= 3;

                // Check for PDF attachments
                bool attachmentMatch = HasPOAttachments(mailItem);

                // Check for structured data patterns
                bool hasStructuredData = HasStructuredData(body);

                // Check for email patterns
                bool hasEmailPatterns = HasEmailPatterns(body);

                // Calculate confidence score
                int confidence = 0;
                if (subjectMatch) confidence += 35;
                if (bodyMatch) confidence += 30;
                if (attachmentMatch) confidence += 25;
                if (hasStructuredData) confidence += 20;
                if (hasEmailPatterns) confidence += 15;

                // Additional bonus for multiple indicators
                int indicatorCount = new[] { subjectMatch, bodyMatch, attachmentMatch, hasStructuredData, hasEmailPatterns }
                    .Count(x => x);
                if (indicatorCount >= 4) confidence += 10;

                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: PO detection confidence: {confidence}% " +
                    $"(subject: {subjectMatch}, body: {bodyMatch}, attachments: {attachmentMatch}, " +
                    $"structured: {hasStructuredData}, patterns: {hasEmailPatterns})");

                return confidence >= 50;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO: EmailDetector error - {ex.Message}");
                return false;
            }
        }

        private string GetEmailBody(Outlook.MailItem mailItem)
        {
            try
            {
                // Try to get HTML body first, then plain text
                if (!string.IsNullOrEmpty(mailItem.HTMLBody))
                {
                    // Strip HTML tags for analysis
                    return System.Text.RegularExpressions.Regex.Replace(mailItem.HTMLBody, "<.*?>", " ");
                }
                return mailItem.Body ?? "";
            }
            catch
            {
                return mailItem.Body ?? "";
            }
        }

        private bool HasPOAttachments(Outlook.MailItem mailItem)
        {
            try
            {
                if (mailItem.Attachments == null) return false;

                for (int i = 1; i <= mailItem.Attachments.Count; i++)
                {
                    var attachment = mailItem.Attachments[i];
                    string fileName = attachment.FileName.ToLower();

                    if (fileName.EndsWith(".pdf") ||
                        fileName.Contains("po") ||
                        fileName.Contains("order") ||
                        fileName.Contains("quote") ||
                        fileName.Contains("invoice") ||
                        fileName.Contains("purchase") ||
                        fileName.Contains("billing"))
                    {
                        return true;
                    }
                }
                return false;
            }
            catch
            {
                return false;
            }
        }

        private bool HasStructuredData(string body)
        {
            return System.Text.RegularExpressions.Regex.IsMatch(body, @"\b\d{4,}\b") || // PO numbers
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"\$\d+\.\d{2}") || // Prices
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"\b\d+\s+(ea|each|pcs|pieces|units?)\b", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase) || // Quantities
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"\b\d{1,2}\/\d{1,2}\/\d{2,4}\b") || // Dates
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"\b[A-Z]{2,}\d{3,}\b"); // Part numbers
        }

        private bool HasEmailPatterns(string body)
        {
            return System.Text.RegularExpressions.Regex.IsMatch(body, @"order\s+number", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase) ||
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"po\s+number", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase) ||
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"purchase\s+order", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase) ||
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"bill\s+to", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase) ||
                   System.Text.RegularExpressions.Regex.IsMatch(body, @"ship\s+to", 
                       System.Text.RegularExpressions.RegexOptions.IgnoreCase);
        }
    }
}
