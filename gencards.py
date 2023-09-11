import sys
import genanki
import configparser
import random
import time
from chinese import ChineseAnalyzer
from dragonmapper import transcriptions, hanzi
import csv
from azure.ai.translation.text import TextTranslationClient, TranslatorCredential
from azure.ai.translation.text.models import InputTextItem
import azure.cognitiveservices.speech as speechsdk
import pathlib
import unicodedata
import re
import os
import shutil
import openai
from io import StringIO
import logging

def generate_id():
    return str(random.randrange(1 << 30, 1 << 31))

config = configparser.ConfigParser()

config.read('config.ini')

if not config.has_section('model'):
    config.add_section('model')

model_config = config['model']

if not config.has_option('model', 'deck_id'):
    config['model']['deck_id'] = generate_id()

if not config.has_option('model', 'word_model_id'):
    config['model']['word_model_id'] = generate_id()

if not config.has_option('model', 'sentence_model_id'):
    config['model']['sentence_model_id'] = generate_id()

if not config.has_section('azure'):
    config.add_section('azure')

azure_config = config['azure']

if not config.has_option('azure', 'translator_api_key'):
    print('Missing Microsoft Azure Translator Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['translator_api_key'] = input('Translator API Key: ')

if not config.has_option('azure', 'translator_api_endpoint'):
    print('Missing Microsoft Azure Translator Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['translator_api_endpoint'] = input('Translator API Endpoint: ')

if not config.has_option('azure', 'speech_api_key'):
    print('Missing Microsoft Azure Speech Config. See here: https://learn.microsoft.com/en-GB/azure/cognitive-services/speech-service/get-started-text-to-speech?tabs=windows%2Cterminal&pivots=programming-language-python')
    config['azure']['speech_api_key'] = input('Speech API Key: ')

if not config.has_option('azure', 'speech_api_endpoint'):
    print('Missing Microsoft Azure Speech Config. See here: https://learn.microsoft.com/en-GB/azure/cognitive-services/speech-service/get-started-text-to-speech?tabs=windows%2Cterminal&pivots=programming-language-python')
    config['azure']['speech_api_endpoint'] = input('Speech API Endpoint: ')

if not config.has_option('azure', 'region'):
    print('Missing Microsoft Azure Config. See here: https://learn.microsoft.com/en-us/azure/cognitive-services/translator/text-sdk-overview?tabs=python')
    config['azure']['region'] = input('Azure Region: ')

if not config.has_option('azure', 'speech_api_voice_name'):
    config['azure']['speech_api_voice_name'] = 'zh-TW-YunJheNeural'

if not config.has_section('mandarin'):
    config.add_section('mandarin')

mandarin_config = config['mandarin']

if not config.has_option('mandarin', 'is_trad'):
    config['mandarin']['is_trad'] = 'false'

if not config.has_option('mandarin', 'reading_format'):
    config['mandarin']['reading_format'] = 'pinyin'

is_trad = mandarin_config.getboolean('is_trad')
reading_format = mandarin_config.get('reading_format')

if not config.has_section('openai'):
    config.add_section('openai')

openai_config = config['openai']

if not config.has_option('openai', 'is_chatgpt_enabled'):
    config['openai']['is_chatgpt_enabled'] = 'false'

is_chatgpt_enabled = openai_config.getboolean('is_chatgpt_enabled')

if is_chatgpt_enabled:
    if not config.has_option('openai', 'api_key'):
        print('Missing OpenAi Config. See here: https://platform.openai.com/docs/api-reference/authentication')
        config['openai']['api_key'] = input('OpenAi API Key: ')

    if not config.has_option('openai', 'organisation'):
        print('Missing OpenAi Config. See here: https://platform.openai.com/docs/api-reference/authentication')
        config['openai']['organisation'] = input('Organisation ID: ')

with open('config.ini', 'w') as configfile:
    config.write(configfile)

translator_credential = TranslatorCredential(azure_config.get('translator_api_key'), azure_config.get('region'))
text_translator = TextTranslationClient(endpoint=azure_config.get('translator_api_endpoint'), credential=translator_credential)

speech_config = speechsdk.SpeechConfig(subscription=azure_config.get('speech_api_key'), region=azure_config.get('region'))
speech_config.speech_synthesis_voice_name = azure_config.get('speech_api_voice_name')
if is_chatgpt_enabled:
    openai.organization = openai_config.get('organisation')
    openai.api_key = openai_config.get('api_key')

logger = logging.getLogger('gencards')
logger.setLevel(logging.DEBUG)

stdout = logging.StreamHandler(sys.stdout)
stdout.setLevel(logging.INFO)

errlogfile = logging.FileHandler('errlog.txt', mode='w', encoding='utf-8')
errlogfile.setLevel(logging.ERROR)

logfile = logging.FileHandler('log.txt', mode='w', encoding='utf-8')
logfile.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
errlogfile.setFormatter(formatter)
logfile.setFormatter(formatter)

logger.addHandler(stdout)
logger.addHandler(errlogfile)
logger.addHandler(logfile)

deck = genanki.Deck(
    model_config.getint('deck_id'),
    'Generated Mandarin Flashcards'
)

word_model = genanki.Model(
    model_config.getint('word_model_id'),
    'Mandarin Word',
    fields=[
        {'name': 'timestamp'},
        {'name': 'Hanzi'},
        {'name': 'Definition'},
        {'name': 'Audio'},
        {'name': 'Reading'},
        {'name': 'Similar Words'}
    ],
    templates=[
        {
            'name': 'Listening',
            'qfmt': 'Listen.{{Audio}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Hanzi}}<br>{{Reading}}<br>{{Definition}}
                <hr id=answer>
                {{Similar Words}}
            '''
        },
        {
            'name': 'Reading',
            'qfmt': '{{Hanzi}}',
            'afmt': '''
                {{FrontSide}}
                <hr id=answer>
                {{Reading}}<br>{{Definition}}<br>{{Audio}}
                <hr id=answer>
                {{Similar Words}}
            '''
        }
    ],
    css='''
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
    '''
)
deck.add_model(word_model)

sentence_model = genanki.Model(
        model_config.getint('sentence_model_id'),
        'Mandarin Sentence',
        fields=[
            {'name': 'timestamp'},
            {'name': 'Hanzi'},
            {'name': 'Meaning'},
            {'name': 'Audio'},
            {'name': 'Reading'},
        ],
        templates=[
            {
                'name': 'Listening',
                'qfmt': 'Listen.{{Audio}}',
                'afmt': '''
                    {{FrontSide}}
                    <hr id=answer>
                    {{Hanzi}}<br>{{Reading}}<br>{{Meaning}}
                '''
            },
            {
                'name': 'Reading',
                'qfmt': '{{Hanzi}}',
                'afmt': '''
                    {{FrontSide}}
                    <hr id=answer>
                    {{Reading}}<br>{{Meaning}}<br>{{Audio}}
                '''
            }
        ],
        css='''
            .card {
                font-family: arial;
                font-size: 20px;
                text-align: center;
                color: black;
                background-color: white;
            }

            .starred {
                color: red;
            }
        '''
    )
deck.add_model(sentence_model)

try: #Make tmp directory if not exists
    os.makedirs('tmp')
except OSError as e:
    e
media_files = []

analyser = ChineseAnalyzer()

def build_word(hanzi, definition, audio, reading, similar_words):
    word_note = genanki.Note(
                    model=word_model,
                    fields=[
                        str(time.time_ns()),
                        hanzi,
                        definition,
                        audio,
                        reading,
                        similar_words
                    ]
                )
    
    return word_note

def build_sentence(hanzi, definition, audio, reading):
    sentence_note = genanki.Note(
                    model=sentence_model,
                    fields=[
                        str(time.time_ns()),
                        hanzi,
                        definition,
                        audio,
                        reading
                    ]
                )
    
    return sentence_note

def transliterate_hanzi(hanzi):
    logger.debug('Transliterating Hanzi')
    language = 'zh-Hant' if is_trad else 'zh-Hans'
    from_script = 'Hant' if is_trad else 'Hans'
    to_script = 'Latn'
    text_to_transliterate = [InputTextItem(text = hanzi)]

    transliteration_response = text_translator.transliterate(content=text_to_transliterate,
                                                                            language=language,
                                                                            from_script=from_script,
                                                                            to_script=to_script)
    transliteration = transliteration_response[0]
    reading = transliteration.text
    if reading_format == 'zhuyin':
        try:
            reading = transcriptions.pinyin_to_zhuyin(transliteration.text)
        except Exception as e:
            logger.error(e)
            logger.warning("Tried and Failed to transliterate Pinyin to Zhuyin. Falling back to Pinyin.")
    logger.debug('Transliteration Successful: {0}'.format(reading))
    return reading

def translate_hanzi(hanzi):
    logger.debug('Translating Hanzi')
    from_script = 'Hant' if is_trad else 'Hans'
    from_language = 'zh-Hant' if is_trad else 'zh_Hans'
    target_languages = ['en']
    text_to_translate = [InputTextItem(text = hanzi)]
    translation_response = text_translator.translate(content=text_to_translate,
                                                                   from_parameter=from_language,
                                                                   from_script=from_script,
                                                                   to=target_languages)
    translation = translation_response[0] if translation_response else None

    if translation:
        first_translation = translation.translations[0]
        if first_translation:
            definition = first_translation.text
    logger.debug('Translation Successful: {0}'.format(definition))
    return definition

def synthesize_text(text):
    logger.debug('Synthesizing text')
    # https://github.com/django/django/blob/master/django/utils/text.py
    normalised_text = unicodedata.normalize('NFKC', text)
    normalised_text = re.sub(r'[^\w\s-]', '', normalised_text.lower())
    normalised_text = re.sub(r'[-\s]+', '-', normalised_text).strip('-_')
    normalised_text += '.wav'

    path = pathlib.Path('tmp', normalised_text)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    result = speech_synthesizer.speak_text_async(text).get()
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file(str(path))

    media_files.append(str(path))

    logger.debug('Synthesized successfully, written to file {0}'.format(str(path)))
    return '[sound:' + normalised_text + ']'

def generate_similar_words(word):
    if is_chatgpt_enabled:
        logger.debug('Generating Similar Words with ChatGPT')
        for i in range(0, 3):
            try:
                language = 'Traditional Mandarin' if is_trad else 'Simplified Mandarin'
                chat_completion = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[
                        {
                            'role': 'system',
                            'content': 'You are a Taiwanese Mandarin Study Assistant generating study material'
                        },
                        {
                            'role': 'user',
                            'content': 
    '''Generate 5 words closely related to """{0}""" which are used commonly in Taiwanese Mandarin.
    You should provide the words in {1}, the readings in Pinyin, and the English Translation, all in CSV format.'''.format(word, language)
                        }
                    ])
                message = chat_completion.choices[0].message.content
                linereader = csv.reader(StringIO(message))
                rows = []
                for row in linereader:
                    if len(row) == 3:
                        if reading_format != 'pinyin' and hanzi.has_chinese(row[0]):
                            try:
                                row[1] = transcriptions.pinyin_to_zhuyin(row[1])
                            except ValueError as e:
                                logger.exception(e)
                                logger.warning('Error converting Pinyin to Zhuyin. Will stick with Pinyin for now.')
                                pass
                        for i in range(0, len(row)):
                            if ',' in row[i]:
                                row[i] = '"' + row[i] + '"'
                        rows.append(', '.join(row))
                message = '<br>'.join(rows)
                logger.debug('Similar Words Generated: {0}'.format(message))
                return message
            except openai.error.APIError as e:
                logger.exception(e)
                logger.warning('OpenAI exception, info written to errlog, retrying {0}th time'.format(i))
            except openai.error.RateLimitError as e:
                logger.exception(e)
                logger.warning('Reached OpenAI rate limit of 3 per minute. Waiting one minute before trying again.')
                time.sleep(60)
    logger.warning('Retried unsuccessfully three times, giving up and returning -')
    return '-'

def find_all(source_string, search_char):
    return [i for i, character in enumerate(source_string) if character == search_char]

with open('input.csv', encoding='utf-8') as input_file:
    linereader = csv.reader(input_file, skipinitialspace=True)
    for row in linereader:
        if len(row) > 0:
            mandarin = row[0]
            analysis = analyser.parse(mandarin, traditional=is_trad)
            if len(analysis.tokens()) == 1: #Single Word
                logger.info('Found Word: {0}'.format(mandarin))
                reading = ''
                word_info = analysis[mandarin][0]
                definition = ''
                if len(row) == 2:
                    definition = row[1]
                elif word_info.definitions is not None:
                    definition = ', '.join(word_info.definitions)
                else:
                    definition = translate_hanzi(mandarin)
                    reading = transliterate_hanzi(mandarin)
                audio = synthesize_text(mandarin)
                if reading == '':
                    reading = analysis.pinyin()
                    if reading_format == 'zhuyin':
                        try:
                            reading = transcriptions.pinyin_to_zhuyin(analysis.pinyin())
                        except Exception as e:
                            logger.error(e)
                            logger.warning("transliteration.text")
                similar_words = generate_similar_words(mandarin)
                word_note = build_word(mandarin, definition, audio, reading, similar_words)
                deck.add_note(word_note)
            else: #Sentence
                logger.info('Found Sentence: {0}'.format(mandarin))
                star_locations = []
                starred_hanzi = []
                if '*' in mandarin:
                    star_locations = find_all(mandarin, '*')
                    for i in range(0, len(star_locations), 2):
                        if len(star_locations) >= i+2:
                            starred_hanzi.append(mandarin[star_locations[i]+1:star_locations[i+1]])
                    mandarin = mandarin.replace('*', '')
                    logger.debug('Found and extracted starred words: {0}'.format(starred_hanzi))
                definition = ''
                if len(row) == 2:
                    definition = row[1]
                else:
                    definition = translate_hanzi(mandarin)
                audio = synthesize_text(mandarin)
                reading = transliterate_hanzi(mandarin)
                if len(starred_hanzi) != 0:
                    starred_reading = map(lambda selected_character: hanzi.to_pinyin(selected_character, all_readings=True)[1:-1].split('/') if reading_format == 'pinyin' else hanzi.to_zhuyin(selected_character, all_readings=True)[1:-1].split('/'), starred_hanzi)
                    for selected_character in starred_hanzi:
                        i = mandarin.index(selected_character)
                        output_string = mandarin[:i] + '<span class=starred>' + selected_character + '</span>' + mandarin[i + len(selected_character):]
                        mandarin = output_string
                    for selected_character in starred_reading:
                        i = -1
                        correct_reading = 0
                        for one_reading in selected_character:
                            try:
                                i = reading.index(one_reading)
                                break
                            except ValueError:
                                logger.debug('Reading wasnt found, checking other readings')
                                correct_reading += 1
                        if i >= 0:
                            output_string = reading[:i] + '<span class=starred>' + selected_character[correct_reading] + '</span>' + reading[i + len(selected_character[correct_reading]):]
                            reading = output_string
                sentence_note = build_sentence(mandarin, definition, audio, reading)
                deck.add_note(sentence_note)
            logger.info('')

output_package = genanki.Package(deck)
output_package.media_files = media_files
output_package.write_to_file('output.apkg')

shutil.rmtree('tmp')