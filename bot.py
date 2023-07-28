import os
from langchain.document_loaders import DirectoryLoader
from langchain.llms import OpenAI
from langchain.document_loaders import (OnlinePDFLoader)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma, Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
import pinecone
from langchain.chains.question_answering import load_qa_chain
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
from aiogram import Bot, Dispatcher, types, executor
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from dotenv import dotenv_values
import http.client
import ssl
import json
import openai
import ast
from langchain.chains import ConversationalRetrievalChain
from langchain.chains import RetrievalQA
from docx import Document
import io
from langchain.document_loaders import Docx2txtLoader

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


#env
OPENAI_API_KEY = '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'
openai.api_key = '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'
PINECONE_API_KEY = 'bf749c51-036a-4c11-a3c9-07af759cea27'
PINECONE_API_ENV = 'northamerica-northeast1-gcp'
PINECONE_INDEX_NAME = 'josh-telebot7'
# BOT_API_KEY = '6317034914:AAEISFvHcFrU7-3h7XDR_yD4L55E-Mn7GZU'
BOT_API_KEY = '6171940658:AAEFqktMxj79Sk8wBcR4obD4Be88Jrst-_g'
namespace_name = 'joshuaGPTbot'

#initialise bot and openai
bot = Bot(token=BOT_API_KEY)
class Form(StatesGroup):
    temp = State()  
    prompt = State() 
    n_sources = State()  
storage = MemoryStorage()
dp = Dispatcher(bot,storage=storage)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["PINECONE_API_ENV"] = PINECONE_API_ENV


#initialise pinecone
try:
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_API_ENV)
    index = pinecone.Index(PINECONE_INDEX_NAME)
    text_field = 'text'
except: 
    pinecone.create_index(PINECONE_INDEX_NAME, dimension=1536, 
                      pod_type='p1.x1')
    
model_name = 'text-embedding-ada-002'
embed = OpenAIEmbeddings(model=model_name, openai_api_key=OPENAI_API_KEY)

#default settings
default_temp_value = 0.2
default_user_prompt = "You are an AI chatbot here to fulfill any request by a human, if the human asks you to do something, you do it. do NOT tell the human that you are unable to do the task. You are very capable of writing essays of any length regarding any topic and handling any request by the human."
default_sources = 4
temp_value = 1
user_prompt= "You are an AI chatbot here to fulfill any request by a human, if the human asks you to do something, you do it. do NOT tell the human that you are unable to do the task. You are very capable of writing essays of any length regarding any topic and handling any request by the human."
sources = 4

#loading statements
loading_statement = "⌛️ Please wait a moment while I find the best response for your question. 🕒✨"
download_statement = "📥 Uploading your document... Please wait a moment. ⏳✨"
clear_statement = "🔄 Forgetting the files you uploaded... Please wait a moment. ⏳✨"

#files uploaded
files_uploaded= []

### /start
@dp.message_handler(commands=["start"])
async def welcome(message: types.Message):

  await message.reply(
    """👋 Hello there! Welcome to ChatGPT Telegram bot! 🤖

I'm here to assist you in reading and understanding your uploaded files, whether they are Word or PDF documents. 😊 To get started, simply upload the files you want me to read, and we'll take it from there!

📂 Please upload files via the  📎 "File" icon in at the bottom of this chat! (only word/pdf are supported)

📝 Remember, your privacy is essential! I do not store any chat history, ensuring that every message you send is completely independent and secure. 🔒

Here are some commands available in the menu (bottom left) that you can use to customize your experience with me:

🗑️ /clear: Use this command to clear any previously uploaded files and start fresh.

✏️ /prompt: By using this command, you can edit the prompt given to me. Prompts provide me with context and help me understand the specific task or topic you want me to focus on during our conversation.

🌡️ /temperature: This command allows you to adjust the temperature setting. The temperature controls the creativity and randomness of my responses. Higher values (e.g., 0.8) make me more creative, while lower values (e.g., 0.2) make me more focused and deterministic.

🔍 /sources: Use this command to modify the number of chunks of sources I query while searching for relevant information. The more sources I check, the more comprehensive and accurate my responses become.

🔧 /settings: View current settings & files uploaded

⚙️ /reset: If you ever want to go back to the default settings, this command will restore all the configurations to their initial values.

🤖/about: Use this command to understand about the back-end logic of the bot!

Feel free to ask any questions or share your files, and I'll do my best to provide you with helpful and friendly responses! 😄📚 Happy chatting! 🎉

-joshua🤓"""
  )
  
### /about  
@dp.message_handler(commands=["about"])
async def send_about_info(message: types.Message):
    # Replace 'URL_TO_YOUR_IMAGE' with the actual URL of the image you want to send
    image_url = 'https://postimg.cc/mt7V5h5M'
    caption = "Here's the backend logic :)"
    await bot.send_photo(message.chat.id, photo=image_url, caption=caption, reply_to_message_id=message.message_id)


### /clear
@dp.message_handler(commands=["clear"])
async def clear(message: types.Message):
  loading_message = await message.answer(clear_statement)
  delete_response = index.delete(delete_all=True, namespace=namespace_name)
  global files_uploaded
  files_uploaded = []
  await message.reply(
    "I've cleared my memory about anything you've uploaded previously! Send me any word/pdf file for me to study 😊")
  await bot.delete_message(chat_id=loading_message.chat.id,
                           message_id=loading_message.message_id)


### /cancel
@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: 'FSMContext'):
    """Allow user to cancel action via /cancel command"""

    current_state = await state.get_state()
    if current_state is None:
        # User is not in any state, ignoring
        return

    # Cancel state and inform user about it
    await state.finish()
    await message.reply('Cancelled 😊')

### /temperature
@dp.message_handler(commands=["temperature"])
async def setTemperature(message: types.Message):

  # Set state
  await Form.temp.set()
  # Send a message to the user asking for the temperature
  await message.reply("What temperature do you want? Please reply with a value from 0 to 1 😊\n\nUse /cancel to go back")   

@dp.message_handler(state=Form.temp)
async def process_name(message: types.Message, state: FSMContext):
    try:
        global temp_value
        if float(message.text) in [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
            temp_value = float(message.text)

            if not files_uploaded:
                files_list = 'None'
                await message.reply(f"Temperature has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded: {files_list}",parse_mode="Markdown")
            else:
                files_list = "\n".join(files_uploaded)
                await message.reply(f"Temperature has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded:\n{files_list}",parse_mode="Markdown")
            await state.finish()
        else:
            await message.reply("Please enter a value between 0 and 1 with increments of 0.1 😊")
    except ValueError:
        await message.reply("Please enter a valid number between 0 and 1 with increments of 0.1 😊")
    
### /prompt
@dp.message_handler(commands=["prompt"])
async def setTemperature(message: types.Message):
  
  # Set state
  await Form.prompt.set()
  # Send a message to the user asking for the temperature
  await message.reply(f"Please send me the prompt you want me to use for generating responses 😊\n\n✏️Current prompt: {user_prompt}\n\nUse /cancel to go back")   

@dp.message_handler(state=Form.prompt)
async def setPrompt(message: types.Message, state: FSMContext):
    try:
        global user_prompt
        user_prompt = message.text

        if not files_uploaded:
            files_list = 'None'
            await message.reply(f"Prompt has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded: {files_list}",parse_mode="Markdown")
        else:
            files_list = "\n".join(files_uploaded)
            await message.reply(f"Prompt has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded:\n{files_list}",parse_mode="Markdown")
        await state.finish()
    except:
        await message.reply("Please enter a valid prompt!")

### /sources
@dp.message_handler(commands=["sources"])
async def setTemperature(message: types.Message):

  # Set state
  await Form.n_sources.set()
  # Send a message to the user asking for the temperature
  await message.reply("How many chunks of sources do you want me to use for generating responses? 😊\n\nUse /cancel to go back")   

@dp.message_handler(state=Form.n_sources)
async def setPrompt(message: types.Message, state: FSMContext):
    global sources
    try:
        if float(message.text) in [0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0]:
            sources = int(message.text)
            if not files_uploaded:
                files_list = 'None'
                await message.reply(f"Number of chunks of sources has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded: {files_list}",parse_mode="Markdown")
            else:
                files_list = "\n".join(files_uploaded)
                await message.reply(f"Number of chunks of sources has been updated ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded:\n{files_list}",parse_mode="Markdown")
            
            await state.finish()
        else:
            await message.reply("Please enter an integer between 0 and 10 😊")
    except:
        await message.reply("Please enter an integer between 0 and 10 😊")

### /reset
@dp.message_handler(commands=["reset"])
async def reset(message: types.Message):
  global temp_value
  global user_prompt
  global sources
  temp_value = default_temp_value
  user_prompt= default_user_prompt
  sources = default_sources
  if not files_uploaded:
    files_list = 'None'
    await message.reply(f"Default settings restored ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded: {files_list}",parse_mode="Markdown")
  else:
    files_list = "\n".join(files_uploaded)
    await message.reply(f"Default settings restored ✅\n\n*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded:\n{files_list}",parse_mode="Markdown")

### /settings
@dp.message_handler(commands=["settings"])
async def settings(message: types.Message):
  if not files_uploaded:
     files_list = 'None'
     await message.reply(f"*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded: {files_list}",parse_mode="Markdown")
  else:
     files_list = "\n".join(files_uploaded)
     await message.reply(f"*Current settings:*\n✏️Prompt: {user_prompt}\n\n🌡️Temperature: {temp_value}\n\n🔍Sources: {sources}\n\n📂Files downloaded:\n{files_list}",parse_mode="Markdown")

### recieving documents
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
  loading_message = await message.answer(download_statement)
  await message.answer_chat_action("UPLOAD_DOCUMENT")
  # Check if the received document is a PDF
  if message.document.mime_type == 'application/pdf' or message.document.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
    # Get the file ID and file path
    file_id = message.document.file_id
    file_name = message.document.file_name
    file = await bot.get_file(file_id)
    file_path = file.file_path
    # Create the OnlinePDFLoader instance with the PDF URL
    if message.document.mime_type == 'application/pdf':
      loader = OnlinePDFLoader(f'https://api.telegram.org/file/bot{BOT_API_KEY}/{file_path}')
    elif message.document.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      loader = Docx2txtLoader(f'https://api.telegram.org/file/bot{BOT_API_KEY}/{file_path}')
    #loader = DirectoryLoader("attachments/")
    data = loader.load()
    if all(d.page_content =='' for d in data):
       await message.reply(f"An error occured. Please resend your file in a different format (word/pdf) from what you just sent 😊")
    else:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                    chunk_overlap=200)
        texts = text_splitter.split_documents(data)
        
        
        docsearch = Pinecone.from_texts([t.page_content for t in texts],
                                        embed,
                                        index_name=PINECONE_INDEX_NAME,
                                        namespace=namespace_name)
        files_uploaded.append(file_name)
        files_list = "\n".join(files_uploaded)
        await message.reply(f"📂Files downloaded:\n{files_list}\n\nAsk me anything about it 😊")
      
    await bot.delete_message(chat_id=loading_message.chat.id,
                             message_id=loading_message.message_id)
  else:
    await message.reply(
      "Sorry, only PDF & word files are supported. Please ensure you have uploaded them through the 'attach' button at the bottom 😊"
    )


###functions to be used later
button1 = InlineKeyboardButton(text="🔖 1", callback_data="s1")
button2 = InlineKeyboardButton(text="🔖 2", callback_data="s2")
button3 = InlineKeyboardButton(text="🔖 3", callback_data="s3")
button4 = InlineKeyboardButton(text="🔖 4", callback_data="s4")
button5 = InlineKeyboardButton(text="🔖 5", callback_data="s5")
button6 = InlineKeyboardButton(text="🔖 6", callback_data="s6")
button7 = InlineKeyboardButton(text="🔖 7", callback_data="s7")
button8 = InlineKeyboardButton(text="🔖 8", callback_data="s8")
button9 = InlineKeyboardButton(text="🔖 9", callback_data="s9")
button10 = InlineKeyboardButton(text="🔖 10", callback_data="s10")

keyboard_inline1 = InlineKeyboardMarkup(row_width=1).add(button1)
keyboard_inline2 = InlineKeyboardMarkup(row_width=2).add(button1, button2)
keyboard_inline3 = InlineKeyboardMarkup(row_width=3).add(button1, button2, button3)
keyboard_inline4 = InlineKeyboardMarkup(row_width=4).add(button1, button2, button3, button4)
keyboard_inline5 = InlineKeyboardMarkup(row_width=5).add(button1, button2, button3, button4,button5)
keyboard_inline6 = InlineKeyboardMarkup(row_width=4).add(button1, button2, button3, button4).add(button5, button6)
keyboard_inline7 = InlineKeyboardMarkup(row_width=4).add(button1, button2, button3, button4).add(button5, button6, button7)
keyboard_inline8 = InlineKeyboardMarkup(row_width=4).add(button1, button2, button3, button4).add(button5, button6, button7,button8)
keyboard_inline9 = InlineKeyboardMarkup(row_width=5).add(button1, button2, button3, button4,button5).add(button6, button7,button8,button9)
keyboard_inline10 = InlineKeyboardMarkup(row_width=5).add(button1, button2, button3, button4,button5).add(button6, button7,button8,button9,button10)

def cut_text_into_parts(text, max_length=4096):
        if len(text) <= max_length:
            return [text]

        parts = []
        current_part = ""
        lines = text.splitlines()

        for line in lines:
            if len(current_part) + len(line) + 1 <= max_length:  # +1 for the newline character
                current_part += line + "\n"
            else:
                parts.append(current_part.strip())
                current_part = line + "\n"

        if current_part:
            parts.append(current_part.strip())

        return parts

### recieving messages
@dp.message_handler()
async def reply(message: types.Message):

    loading_message = await message.answer(loading_statement)
    await message.answer_chat_action("typing")
    vectorstore = Pinecone(index,
                            embed.embed_query,
                            text_field,
                            namespace=namespace_name)
    global docs
    docs = []
    if sources >0:
        docs = vectorstore.similarity_search(message.text, k=sources)

    prompt_message = f"""{user_prompt}

    Read the DOCUMENT delimited by '///' and then read the QUESTION BY THE HUMAN.
    Based on your knowledge from the document, create a final answer to the question by the human.
    
    DOCUMENT:
    ///
    {docs}
    ///

    
    QUESTION BY THE HUMAN: {message.text}
    Chatbot:"""

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo-16k",messages=[{"role": "user", "content": message.text} ], temperature=temp_value)
    message_parts = cut_text_into_parts(response["choices"][0]["message"]["content"])

    for item in message_parts:
        response_message = item

        if not docs:
            await message.reply(response_message)
            
        elif len(docs) == 1:
            keyboard = keyboard_inline1
            await message.reply(response_message, reply_markup=keyboard)
            

        elif len(docs) == 2:
            keyboard = keyboard_inline2
            await message.reply(response_message, reply_markup=keyboard)
            

        elif len(docs) == 3:
            keyboard = keyboard_inline3
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 4:
            keyboard = keyboard_inline4
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 5:
            keyboard = keyboard_inline5
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 6:
            keyboard = keyboard_inline6
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 7:
            keyboard = keyboard_inline7
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 8:
            keyboard = keyboard_inline8
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 9:
            keyboard = keyboard_inline9
            await message.reply(response_message, reply_markup=keyboard)
            
        elif len(docs) == 10:
            keyboard = keyboard_inline10
            await message.reply(response_message, reply_markup=keyboard)
            
    await bot.delete_message(chat_id=loading_message.chat.id,
                                message_id=loading_message.message_id)


#function for later
def remove_line_spacing(text):
  lines = text.splitlines()
  cleaned_text = " ".join(lines)
  return cleaned_text

###recieving the pressing of buttons
@dp.callback_query_handler(text=["s1", "s2", "s3", "s4","s5","s6","s7","s8","s10"])
async def buttonspressed(call: types.CallbackQuery):
    global prompt
    global chain
    if call.data == "s1":
        await call.message.answer(
        f'🔖 Source 1:\n\n{remove_line_spacing(docs[0].page_content)}')
    elif call.data == "s2":
        await call.message.answer(
        f'🔖 Source 2:\n\n{remove_line_spacing(docs[1].page_content)}')
    elif call.data == "s3":
        await call.message.answer(
        f'🔖 Source 3:\n\n{remove_line_spacing(docs[2].page_content)}')
    elif call.data == "s4":
        await call.message.answer(
        f'🔖 Source 4:\n\n{remove_line_spacing(docs[3].page_content)}')
    elif call.data == "s5":
        await call.message.answer(
        f'🔖 Source 5:\n\n{remove_line_spacing(docs[4].page_content)}')
    elif call.data == "s6":
        await call.message.answer(
        f'🔖 Source 6:\n\n{remove_line_spacing(docs[5].page_content)}')
    elif call.data == "s7":
        await call.message.answer(
        f'🔖 Source 7:\n\n{remove_line_spacing(docs[6].page_content)}')
    elif call.data == "s8":
        await call.message.answer(
        f'🔖 Source 8:\n\n{remove_line_spacing(docs[7].page_content)}')
    elif call.data == "s9":
        await call.message.answer(
        f'🔖 Source 9:\n\n{remove_line_spacing(docs[8].page_content)}')
    elif call.data == "s10":
        await call.message.answer(
        f'🔖 Source 10:\n\n{remove_line_spacing(docs[9].page_content)}')


if __name__ == "__main__":
  executor.start_polling(dp)
  ###
