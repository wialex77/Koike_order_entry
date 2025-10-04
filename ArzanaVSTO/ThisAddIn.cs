using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Xml.Linq;
using Outlook = Microsoft.Office.Interop.Outlook;
using Office = Microsoft.Office.Core;
using Microsoft.Office.Tools.Outlook;

namespace ArzanaVSTO
{
    public partial class ThisAddIn
    {
        private POProcessor poProcessor;
        private EmailDetector emailDetector;

        private void ThisAddIn_Startup(object sender, System.EventArgs e)
        {
            try
            {
                // Initialize components
                emailDetector = new EmailDetector();
                poProcessor = new POProcessor();

                // Subscribe to NewMailEx event for automatic processing
                this.Application.NewMailEx += Application_NewMailEx;

                // Log startup
                System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: Started successfully");
                System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: NewMailEx event subscribed");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: Startup error - {ex.Message}");
            }
        }

        private void Application_NewMailEx(string EntryIDCollection)
        {
            try
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: NewMailEx triggered for EntryID: {EntryIDCollection}");

                // Get the mail item from the Entry ID
                Outlook.MailItem mailItem = this.Application.Session.GetItemFromID(EntryIDCollection) as Outlook.MailItem;
                
                if (mailItem != null)
                {
                    System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: Processing email - Subject: {mailItem.Subject}");

                    // Check if this is a PO email
                    if (emailDetector.IsPOEmail(mailItem))
                    {
                        System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: PO email detected, processing...");
                        
                        // Process the PO email
                        ProcessPOEmail(mailItem);
                    }
                    else
                    {
                        System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: Not a PO email, skipping");
                    }
                }
                else
                {
                    System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: Could not retrieve mail item");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: NewMailEx error - {ex.Message}");
            }
        }

        private async void ProcessPOEmail(Outlook.MailItem mailItem)
        {
            try
            {
                // Tag the email as being processed
                string currentCategories = mailItem.Categories ?? "";
                if (!currentCategories.Contains("Arzana-Processing"))
                {
                    mailItem.Categories = currentCategories + (string.IsNullOrEmpty(currentCategories) ? "" : ";") + "Arzana-Processing";
                    mailItem.Save();
                }

                // Process the email
                var result = await poProcessor.ProcessEmailAsync(mailItem);

                // Update the tag based on result
                string newCategory = GetCategoryFromResult(result);
                UpdateEmailCategory(mailItem, newCategory);

                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: Email processed - Status: {result.Status}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: ProcessPOEmail error - {ex.Message}");
                
                // Tag as error
                UpdateEmailCategory(mailItem, "Arzana-Error");
            }
        }

        private string GetCategoryFromResult(ProcessingResult result)
        {
            switch (result.Status)
            {
                case "success":
                    if (result.CustomerMatched && result.PartsMapped > 0)
                        return "Arzana-Ready";
                    else if (result.CustomerMatched)
                        return "Arzana-CustomerMatched";
                    else
                        return "Arzana-NeedsReview";
                case "missing_info":
                    return "Arzana-MissingInfo";
                case "error":
                    return "Arzana-Error";
                default:
                    return "Arzana-Unknown";
            }
        }

        private void UpdateEmailCategory(Outlook.MailItem mailItem, string newCategory)
        {
            try
            {
                // Remove old Arzana categories and add new one
                string currentCategories = mailItem.Categories ?? "";
                string[] categories = currentCategories.Split(';');
                var filteredCategories = categories.Where(c => !c.Trim().StartsWith("Arzana-")).ToList();
                filteredCategories.Add(newCategory);
                
                mailItem.Categories = string.Join(";", filteredCategories);
                mailItem.Save();
                
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: Email tagged as: {newCategory}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: UpdateEmailCategory error - {ex.Message}");
            }
        }

        private void ThisAddIn_Shutdown(object sender, System.EventArgs e)
        {
            try
            {
                // Unsubscribe from events
                this.Application.NewMailEx -= Application_NewMailEx;
                
                System.Diagnostics.Debug.WriteLine("Arzana VSTO Add-in: Shutdown successfully");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Arzana VSTO Add-in: Shutdown error - {ex.Message}");
            }
        }

        #region VSTO generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InternalStartup()
        {
            this.Startup += new System.EventHandler(ThisAddIn_Startup);
            this.Shutdown += new System.EventHandler(ThisAddIn_Shutdown);
        }
        
        #endregion
    }
}
