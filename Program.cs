using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

namespace PdfReader
{
    internal class Program
    {
        static string pdfDirectoryPath;
        static string[] pdfFiles;

        static readonly Regex EmailRegex = new Regex(@"[\w\.\-]+@[\w\.\-]+\.[a-z]{2,6}(?![a-z])", RegexOptions.Compiled);

        static readonly Regex PhoneRegex = new Regex(@"\d{2}(?:[ .]\d{2}){4}", RegexOptions.Compiled);

        static readonly Regex SectorStartRegex = new Regex(@"(ITI|ITE|VMC|PAC|Isolation|Combles|Menuiserie|Photovolta|Poêle|Projet complet|Multi travaux|Chaudière|Chauffage|ECS)", RegexOptions.Compiled);

        static readonly Regex LegendRegex = new Regex(@"Dernière mise à jour[\s\S]*?Eau Chaude Sanitaire", RegexOptions.Compiled);
        static readonly Regex GroupementRegex = new Regex(@"GROUPEMENT D'ENTREPRISES.*?PROFESSIONNELS RGE", RegexOptions.Compiled);
        static readonly Regex HeaderRegex = new Regex(@"Nom de l'entreprise\s*Adresse\s*Téléphone\s*Secteur de travaux\s*Contact e-mail", RegexOptions.Compiled);

        static readonly string[] SectorEndWords = new[]
        {
            "perdus", "murs", "rampants", "toit", "toiture", "terrasse", "terrasses",
            "bas", "bois", "gaz", "electrique", "électrique",
            "photovoltaique", "photovoltaïque", "photovoltaiques", "photovoltaïques",
            "renovation", "rénovation", "extérieur", "thermodynamique",
            "Photovoltaïque", "Thermodynamique", "Photovoltaique",
            "VMC", "Menuiseries", "menuiseries", "solaire"
        };

        static readonly Regex SectorEmailGlueRegex = new Regex($@"(?<=\b(?:{string.Join("|", SectorEndWords.Select(Regex.Escape))}))(?=[\w\.\-]+@)", RegexOptions.Compiled);

        static void Main(string[] args)
        {
            Logger.LogInfo("Starting RGE PDF Reader...");
            pdfDirectoryPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Pdf");
            if (!Directory.Exists(pdfDirectoryPath))
            {
                Logger.LogWarning("Directory 'Pdf' does not exist. Creating...");
                Directory.CreateDirectory(pdfDirectoryPath);
            }
            pdfFiles = Directory.GetFiles(pdfDirectoryPath, "*.pdf");
            Logger.LogInfo($"Found {pdfFiles.Length} PDF files in the directory.");
            if (pdfFiles.Length > 0)
            {
                SendChoices();
            }
            else
            {
                Logger.LogWarning("No PDF files found in the directory. Please add PDF files to the 'Pdf' directory and restart the application.");
                Thread.Sleep(2500);
                Environment.Exit(0);
            }
        }

        static void SendChoices()
        {
            Dictionary<int, string> choices = new Dictionary<int, string>();
            for (int i = 0; i < pdfFiles.Length; i++)
            {
                choices.Add(i, Path.GetFileNameWithoutExtension(pdfFiles[i]));
            }
            Logger.LogAsk("Choose a PDF file to read.", choices);
            while (true)
            {
                string rawChoice = Console.ReadLine();
                if (string.IsNullOrEmpty(rawChoice) || !int.TryParse(rawChoice, out int choice))
                {
                    Logger.LogError("Invalid input. Please enter a valid number corresponding to the PDF file.");
                    continue;
                }
                if (!choices.ContainsKey(choice))
                {
                    Logger.LogError("Invalid choice. Please select a number from the list.");
                    continue;
                }
                HandleChoice(pdfFiles[choice]);
                break;
            }
        }

        static void HandleChoice(string pdfPath)
        {
            Logger.LogInfo($"Reading PDF: {Path.GetFileName(pdfPath)}");
            string rawText = GetTextInPdf(pdfPath);

            Logger.LogInfo("Raw text: " + rawText + "\n\n\n");

            var bizList = Parse(rawText);
            string formatedBizs = string.Join("\n\n\n", bizList.Select(b => b.ToString()));
            Logger.LogInfo($"{bizList.Count} businesses found: " + formatedBizs);
        }

        static string GetTextInPdf(string pdfPath)
        {
            var sb = new StringBuilder();

            using (PdfDocument document = PdfDocument.Open(pdfPath))
            {
                foreach (Page page in document.GetPages())
                {
                    sb.AppendLine(page.Text);
                }
            }

            return sb.ToString();
        }

        static string CleanText(string raw)
        {
            string text = raw;
            text = LegendRegex.Replace(text, "");
            text = GroupementRegex.Replace(text, "");
            text = HeaderRegex.Replace(text, "");
            text = Regex.Replace(text, @"Commune\s*\d*", "");

            text = Regex.Replace(text, @"(?<=\.[a-z]{2,6})\d{1,3}(?=[A-ZÀ-Ü])", "");
            text = Regex.Replace(text, @"[\u00A0\u2000-\u200B\u202F]", " ");

            text = Regex.Replace(text, @"(?<=\d{2})(?=(?:ITI|ITE|VMC|PAC|Isolation|Combles|Menuiserie|Photovolt|Po\u00eale|Projet|Multi|Chaudi\u00e8re|Chauffage|ECS))", " ");

            text = Regex.Replace(text, @"(?<=[a-zA-Zà-ÿ])(?=(?:ZAC|ZI|ZA)\b)", " ", RegexOptions.IgnoreCase);

            text = SectorEmailGlueRegex.Replace(text, " ");

            return text;
        }

        static List<Biz> Parse(string rawText)
        {
            string text = CleanText(rawText);

            var result = new List<Biz>();
            var emailMatches = EmailRegex.Matches(text);
            int previousEnd = 0;

            foreach (Match emailMatch in emailMatches)
            {
                string block = text.Substring(previousEnd, emailMatch.Index + emailMatch.Length - previousEnd).Trim();
                previousEnd = emailMatch.Index + emailMatch.Length;

                var biz = ParseBlock(block, emailMatch.Value);
                if (biz != null)
                    result.Add(biz);
                else
                    Logger.LogWarning($"Block not parsed: {block}");
            }

            return result;
        }

        static Biz ParseBlock(string block, string email)
        {
            var postalMatch = Regex.Match(block, @"\d{5}(?=\s*[A-ZÀ-Ü])");
            if (!postalMatch.Success) return null;

            string beforePostal = block.Substring(0, postalMatch.Index).Trim();
            string afterPostal = block.Substring(postalMatch.Index + 5);

            var phoneMatch = PhoneRegex.Match(afterPostal);

            string city, phone, sectorsText;

            if (phoneMatch.Success)
            {
                city = afterPostal.Substring(0, phoneMatch.Index).Trim();
                phone = phoneMatch.Value;

                int sectorsStart = phoneMatch.Index + phoneMatch.Length;
                int sectorsLength = afterPostal.Length - email.Length - sectorsStart;
                sectorsText = sectorsLength > 0 ? afterPostal.Substring(sectorsStart, sectorsLength).Trim() : "";
            }
            else
            {
                phone = "";
                var sectorMatch = SectorStartRegex.Match(afterPostal);
                if (sectorMatch.Success)
                {
                    city = afterPostal.Substring(0, sectorMatch.Index).Trim();
                    int sectorsLength = afterPostal.Length - email.Length - sectorMatch.Index;
                    sectorsText = sectorsLength > 0 ? afterPostal.Substring(sectorMatch.Index, sectorsLength).Trim() : "";
                }
                else
                {
                    city = "";
                    sectorsText = afterPostal.Replace(email, "").Trim();
                }
            }

            sectorsText = PhoneRegex.Replace(sectorsText, "").Trim().TrimStart(',').Trim();

            city = Regex.Replace(city, @"^\d+\s*", "").Trim();

            var addressStart = Regex.Match(beforePostal, @"\d+\s+[A-ZÀ-Ü]|\b(?:ZAC|ZI|ZA)\b", RegexOptions.IgnoreCase);
            if (!addressStart.Success)
                addressStart = Regex.Match(beforePostal, @"\d");
            string name = addressStart.Success ? beforePostal.Substring(0, addressStart.Index).Trim() : beforePostal;
            string address = addressStart.Success ? beforePostal.Substring(addressStart.Index).Trim() : "";

            return new Biz
            {
                Name = name,
                Adress = address,
                City = $"{postalMatch.Value} {city}".Trim(),
                Phone = phone,
                Sectors = sectorsText.Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToArray(),
                Email = email
            };
        }
    }
}