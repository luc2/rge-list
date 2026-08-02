using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace PdfReader
{
    public class Biz
    {
        public string Name { get; set; }
        public string Adress { get; set; }
        public string City { get; set; }
        public string Phone { get; set; }
        public string[] Sectors { get; set; }
        public string Email { get; set; }

        public override string ToString()
        {
            string str = $"Name: {Name}\nAddress: {Adress}\nCity: {City}\nPhone: {Phone}\nSectors: {string.Join(", ", Sectors)}\nEmail: {Email}";
            return str;
        }
    }
}
