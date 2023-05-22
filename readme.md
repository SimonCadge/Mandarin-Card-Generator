A Python script to automate generating Anki cards for Mandarin Study.
Generate cards for words or for full sentences.
I'm using Microsoft Azure cloud services for translation, transliteration and text-to-speech services.

Words:
You Provide - Mandarin Word, Definition (optional, will be generated if missing)
Generated - Sound, Zhuyin, Related Words

Sentences:
You Provide - Mandarin Sentence, English Translation (optional, will be generated if missing)
Generated - Sound, Zhuyin

Possible stretch goal - Using ChatGPT to generate example sentences.

Input:
csv file in the following format
Mandarin Word/Sentence, Optional Definition/Translation

Output:
Anki apkg file. Import into Anki using File -> Import