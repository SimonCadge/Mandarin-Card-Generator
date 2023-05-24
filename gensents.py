import configparser
import random
from chinese import ChineseAnalyzer
from dragonmapper import transcriptions, hanzi
import csv
import openai
from io import StringIO

def generate_id():
    return str(random.randrange(1 << 30, 1 << 31))

config = configparser.ConfigParser()

config.read('config.ini')

if not config.has_section('mandarin'):
    config.add_section('mandarin')

mandarin_config = config['mandarin']

if not config.has_option('mandarin', 'is_trad'):
    config['mandarin']['is_trad'] = 'false'

if not config.has_option('mandarin', 'reading_format'):
    config['mandarin']['reading_format'] = 'pinyin'

if not config.has_section('openai'):
    config.add_section('openai')

openai_config = config['openai']

if not config.has_option('openai', 'api_key'):
    print('Missing OpenAi Config. See here: https://platform.openai.com/docs/api-reference/authentication')
    config['openai']['api_key'] = input('OpenAi API Key: ')

if not config.has_option('openai', 'organisation'):
    print('Missing OpenAi Config. See here: https://platform.openai.com/docs/api-reference/authentication')
    config['openai']['organisation'] = input('Organisation ID: ')

with open('config.ini', 'w') as configfile:
    config.write(configfile)

openai.organization = openai_config.get('organisation')
openai.api_key = openai_config.get('api_key')

analyser = ChineseAnalyzer()

reading_format = mandarin_config.get('reading_format')
is_trad = mandarin_config.get('is_trad')

def generate_sentences(words):
    for i in range(0, 3):
        try:
            language = 'Traditional Mandarin' if is_trad else 'Simplified Mandarin'
            chat_completion = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[
                    {
                        'role': 'system',
                        'content': 'You are a Taiwanese Mandarin Study Assistant generating example Mandarin sentences.'
                    },
                    {
                        'role': 'user',
                        'content': 
'''Create two example sentences for each of the following Mandarin words.
CSV format with the following columns: {0} Sentence, Pinyin Transliteration, English Translation. Use the pipe(|) character as a delimiter. Don't 
Example row: 她給我很大的安慰.|tā gěi wǒ hěn dà de ān wèi.|She gave me great comfort.
Words: """{1}"""'''.format(language, words)
                    }
                ])
            message = chat_completion.choices[0].message.content
            linereader = csv.reader(StringIO(message), delimiter='|')
            rows = []
            for row in linereader:
                if len(row) == 3:
                    if reading_format != 'pinyin' and hanzi.has_chinese(row[0]):
                        row[1] = transcriptions.pinyin_to_zhuyin(row[1].lower())
                    for i in range(0, len(row)):
                        if ',' in row[i]:
                            row[i] = '"' + row[i] + '"'
                    rows.append(','.join(row))
            message = '\n'.join(rows)
            return message
        except openai.error.APIError:
            print('OpenAI exception, retrying {0}th time'.format(i))
    return '-'

with open('input.csv', encoding='utf-8') as input_file:
    linereader = csv.reader(input_file)
    words = []
    for row in linereader:
        if len(row) > 0:
            mandarin = row[0]
            analysis = analyser.parse(mandarin, traditional=is_trad)
            if len(analysis.tokens()) == 1: #Single Word
                words.append(mandarin)

    generated_sentences = generate_sentences(', '.join(words))

    with open('generated_sentences.csv', 'w', encoding='utf-8') as output_file:
        output_file.write(generated_sentences)