A Python script to automate generating Anki cards for Mandarin Study.
Generate cards for words or for full sentences.

Words:
You Provide - Mandarin Word, Definition
Generated - Sound, Zhuyin, Related Words

Sentences:
You Provide - Mandarin Sentence, English Translation
Generated - Sound, Zhuyin

Possible stretch goal - Using ChatGPT to generate example sentences.

Input:
csv file in the following format
"word", Mandarin Word, Definition
"sentence", Mandarin Sentence, English Translation

Output:
Anki apkg file. Import into Anki using File -> Import