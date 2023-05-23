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
            chat_completion = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[
                    {
                        'role': 'system',
                        'content': 'You are a Taiwanese Mandarin Study Assistant generating example Mandarin sentences.'
                    },
                    {
                        'role': 'user',
                        'content': 'For each of the following words generate 2 example sentences in Traditional Chinese with English translation, and which demonstrate how they are used in Taiwanese Mandarin. The words are ' + words
                    }
                ])
            message = chat_completion.choices[0].message.content
            return message
        except openai.error.APIError:
            print('OpenAI exception, retrying {0}th time'.format(i))
    return '-'

with open('input.csv', encoding='utf-8') as input_file:
    data = input_file.read()
    if data[-1] == '\n':
        data[-1] = ''
    data = data.replace('\n', ', ')

    generated_sentences = generate_sentences(data)

    with open('generated_sentences.csv', 'w', encoding='utf-8') as output_file:
        output_file.write(generated_sentences)