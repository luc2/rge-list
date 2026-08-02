using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace PdfReader
{
    public static class Logger
    {
        private static void Log(string type, ConsoleColor colorType, string message, ConsoleColor messageColor = ConsoleColor.White)
        {
            Console.ForegroundColor = colorType;
            Console.Write(type);
            Console.ForegroundColor = ConsoleColor.Gray;
            Console.Write(": ");
            Console.ForegroundColor = ConsoleColor.White;
            Console.Write(message + "\n");
            Console.ResetColor();
        }

        public static void LogDebug(string message) => Log("debug", ConsoleColor.Gray, message);
        public static void LogInfo(string message) => Log("info", ConsoleColor.Blue, message);
        public static void LogSuccess(string message) => Log("success", ConsoleColor.Green, message);
        public static void LogWarning(string message) => Log("warning", ConsoleColor.Yellow, message);
        public static void LogError(string message) => Log("error", ConsoleColor.Red, message);
        public static void LogException(Exception ex) => Log("exception", ConsoleColor.DarkBlue, ex.ToString());

        public static void LogAsk(string message, Dictionary<int, string> choices)
        {
            Log("ask", ConsoleColor.Cyan, message);
            foreach (var choice in choices)
            {
                Console.ForegroundColor = ConsoleColor.Gray;
                Console.Write("- ");
                Console.ForegroundColor = ConsoleColor.Blue;
                Console.Write(choice.Key);
                Console.ForegroundColor = ConsoleColor.Gray;
                Console.Write(": ");
                Console.ForegroundColor = ConsoleColor.White;
                Console.Write(choice.Value + "\n");
                Console.ResetColor();
            }
        }
        
    }
}
