using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using UglyToad.PdfPig;

namespace PdfRgeBizsReader
{
    /// <summary>
    /// Logique d'interaction pour MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private Regex EmailRegex => new Regex(@"[\w\.\-]+@[\w\.\-]+\.[a-z]{2,6}(?![a-z])", RegexOptions.Compiled);
        private Regex PhoneRegex => new Regex(@"\d{2}(?:[ .]\d{2}){4}", RegexOptions.Compiled);
        private Regex SectorStartRegex => new Regex(@"(ITI|ITE|VMC|PAC|Isolation|Combles|Menuiserie|Photovolta|Poêle|Projet complet|Multi travaux|Chaudière|Chauffage|ECS)", RegexOptions.Compiled);
        private Regex LegendRegex => new Regex(@"Dernière mise à jour[\s\S]*?Eau Chaude Sanitaire", RegexOptions.Compiled);
        private Regex GroupementRegex => new Regex(@"GROUPEMENT D'ENTREPRISES.*?PROFESSIONNELS RGE", RegexOptions.Compiled);
        private Regex HeaderRegex => new Regex(@"Nom de l'entreprise\s*Adresse\s*Téléphone\s*Secteur de travaux\s*Contact e-mail", RegexOptions.Compiled);
        private string[] SectorEndWords => new[]
        {
            "perdus", 
            "murs", 
            "rampants", 
            "toit", 
            "toiture", 
            "terrasse", 
            "terrasses",
            "bas", 
            "bois", 
            "gaz", 
            "electrique", 
            "électrique",
            "photovoltaique", 
            "photovoltaïque", 
            "photovoltaiques", 
            "photovoltaïques",
            "renovation", 
            "rénovation", 
            "extérieur", 
            "thermodynamique",
            "Photovoltaïque", 
            "Thermodynamique", 
            "Photovoltaique",
            "VMC", 
            "Menuiseries", 
            "menuiseries", 
            "solaire"
        };
        private Regex SectorEmailGlueRegex => new Regex($@"(?<=\b(?:{string.Join("|", SectorEndWords.Select(Regex.Escape))}))(?=[\w\.\-]+@)", RegexOptions.Compiled);

        public MainWindow()
        {
            InitializeComponent();
            this.DataContext = this;
            this.Loaded += MainWindow_Loaded;
        }

        public void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            BizsGrid.Visibility = Visibility.Collapsed;
            SelectPdfGrid.Visibility = Visibility.Visible;
            BizsItemsControl.ItemsSource = new ObservableCollection<Biz>();
        }

        private void SelectPdfButton_Click(object sender, RoutedEventArgs e)
        {
            var openFileDialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "PDF Files (*.pdf)|*.pdf",
                Title = "Select a PDF file"
            };
            if (openFileDialog.ShowDialog() == true)
            {
                string pdfPath = openFileDialog.FileName;
                List<Biz> bizs = GetBizs(pdfPath);
                BizsItemsControl.ItemsSource = new ObservableCollection<Biz>(bizs);
                SelectPdfGrid.Visibility = Visibility.Collapsed;
                BizsGrid.Visibility = Visibility.Visible;
            }
        }

        private void BizDetailButton_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button button && button.DataContext is Biz biz)
            {
                MessageBox.Show(biz.ToString(), "Business Details", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private List<Biz> GetBizs(string pdfPath)
        {
            List<Biz> bizs = Parse(GetTextInPdf(pdfPath));
            return bizs;
        }

        private string GetTextInPdf(string pdfPath)
        {
            var sb = new StringBuilder();

            using (PdfDocument document = PdfDocument.Open(pdfPath))
            {
                foreach (UglyToad.PdfPig.Content.Page page in document.GetPages())
                {
                    sb.AppendLine(page.Text);
                }
            }

            return sb.ToString();
        }

        private string CleanText(string raw)
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

        private List<Biz> Parse(string rawText)
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
            }

            return result;
        }

        private Biz ParseBlock(string block, string email)
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
