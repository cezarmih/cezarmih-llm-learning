# Create
# (base) cezarmihaila@CezarMihaila-16MBP-2151 learning % python -m venv agent_tutorial_env
# (base) cezarmihaila@CezarMihaila-16MBP-2151 learning % source agent_tutorial_env/bin/activate

import arxiv
import asyncio
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from litellm import acompletion
import weave
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import wandb 
from datetime import datetime, timedelta

print('Imports done')
print("Current working directory:", os.getcwd())
# Load environment variables from secrets.env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../..', 'secrets.env'))

# Authenticate with W&B using the API key
# Get the WANDB_API_KEY at https://wandb.ai/authorize; https://wandb.ai/home?product=weave
wandb_api_key = os.getenv("WANDB_API_KEY")
wandb.login(key=wandb_api_key)

# Initialize Weave
weave.init("news_agent")

# Email configuration
email = os.getenv("EMAIL")
pswd = os.getenv("EMAIL_PASSWORD")
LAST_EMAIL_FILE = "last_email.json"


# Helper function: Run model inference
async def run_inference(query):
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = "gpt-4o-mini"
    response = await acompletion(
        model=model_name,
        api_key=api_key,
        messages=[{"role": "user", "content": query}],
        temperature=0.7,
        max_tokens=1024,
    )
    return response["choices"][0]["message"]["content"]


# Helper function: Read a prompt from a file
def read_prompt(file_path):
    print("read_prompt from file_path:" + file_path)
    with open(file_path, "r") as file:
        return file.read()


# Helper function: Read a reference article
def read_reference_article(article_file):
    if not os.path.exists(article_file):
        return ""
        
    if article_file.endswith('.pdf'):
        return read_pdf_first_50_pages(article_file)
    else:
        try:
            with open(article_file, "r") as file:
                return file.read().strip()
        except UnicodeDecodeError:
            print(f"Could not read {article_file} as text file")
            return ""


# Helper function: Format Arxiv results
def format_arxiv_results(results):
    return "[" + ",\n".join(
        [
            f'{{"index": {i+1}, "title": "{result["title"]}", "summary": "{result["summary"]}", "url": "{result["url"]}"}}'
            for i, result in enumerate(results)
        ]
    ) + "]"


# Helper function: Convert Arxiv URL to PDF URL
def convert_to_pdf_url(abs_url):
    return abs_url.replace("/abs/", "/pdf/")


# Helper function: Read the first 10 pages of a PDF
def read_pdf_first_50_pages(pdf_path):
    try:
        with open(pdf_path, "rb") as file:
            reader = PdfReader(file)
            return "\n".join(page.extract_text() for page in reader.pages[:50])
    except Exception:
        return ""


# Arxiv search function
@weave.op
def get_arxiv_possibilities(topics, max_results=200):
    # Calculate the date 24 hours ago
    # start_date = datetime.now() - timedelta(days=1)  # Remove this line if not needed
    
    all_results = []
    for topic in topics:
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
            # Remove start_date if not supported
        )
        all_results.extend([
            {"title": result.title, "summary": result.summary.replace("\n", " "), "url": result.entry_id}
            for result in search.results()
        ])
    
    return all_results


# Select the best Arxiv papers with call ID
@weave.op
async def select_best_arxiv_papers(possibilities, prompt_file):
    if not possibilities:
        return None, None, None

    # Get the Weave call ID
    call_id = weave.get_current_call().id
    formatted_results = format_arxiv_results(possibilities)
    selection_prompt = read_prompt(prompt_file)
    query = f"{selection_prompt}\n\nSearch Results:\n{formatted_results}\n\nRespond with ONLY the URLs of the papers you recommend, separated by commas, nothing else."
    selected_response = await run_inference(query)
    selected_urls = [url.strip() for url in selected_response.split(",") if url.strip()]

    # Match the selected URLs to possibilities for additional details
    selected_papers = [
        next((item for item in possibilities if item["url"] in url), None)
        for url in selected_urls
    ]
    selected_papers = [paper for paper in selected_papers if paper is not None]

    return (
        [convert_to_pdf_url(paper["url"]) for paper in selected_papers],
        [paper["title"] for paper in selected_papers],
        call_id,  # Return the Weave call ID
    )


# Generate questions from the paper content
@weave.op
async def generate_questions_from_paper(paper_text, prompt_file):
    print("generate_questions_from_paper")
    # Print only the first 10 lines of the paper_text
    print("paper_text:", "\n".join(paper_text.splitlines()[:10]))
    question_prompt = read_prompt(prompt_file)
    prompt = f"{question_prompt}\n\nText:\n{paper_text}\n\nPlease provide a list of questions."
    return await run_inference(prompt)


# Generate a summary of the paper
@weave.op
async def generate_summary_from_paper(paper_text, questions, summary_prompt_file, reference_text):
    summary_prompt = read_prompt(summary_prompt_file)
    prompt = (
        f"{summary_prompt}\n\nPREVIOUS Reference Article:\n{reference_text}\n\n"
        f"List of Questions to address in the article:\n{questions}\n\nPaper Content:\n{paper_text}"
    )
    return await run_inference(prompt)


# Edit the generated summary
@weave.op
async def edit_summary(summary, editor_prompt_file):
    editor_prompt = read_prompt(editor_prompt_file)
    prompt = f"{editor_prompt}\n\nArticle Content:\n{summary}"
    return await run_inference(prompt)


# Save email details to a file
async def save_last_email(subject, body, call_id=None, call_url=None):
    """Save the subject, body, Weave call ID, and call URL of the last email sent."""
    with open(LAST_EMAIL_FILE, "w") as f:
        json.dump({"subject": subject, "body": body, "call_id": call_id, "call_url": call_url}, f)
    print(f"Saved last email with call ID: {call_id} and URL: {call_url}")




def get_wandb_username():
    try:
        # Initialize the W&B API
        api = wandb.Api()
        # Fetch the username of the authenticated user
        return api.default_entity
    except Exception as e:
        print(f"Error fetching W&B username: {e}")
        return "unknown_user"


# Send an email
async def send_email(subject, body, recipient_email, sender_email, sender_password, main_call_id=None, selection_call_id=None):
    try:
        # Dynamically fetch W&B username
        username = get_wandb_username()
        call_url = f"https://wandb.ai/{username}/news_agent/r/call/{main_call_id}" if main_call_id else None


        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(f"{body}\n\nView the process log: {call_url}", "plain"))


        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())


        print(f"Email sent to {recipient_email}")
        await save_last_email(subject, body, selection_call_id, call_url)
    except Exception as e:
        print(f"Failed to send email: {e}")


# Update the main function to handle multiple selected papers
@weave.op
async def main():
    main_call_id = weave.get_current_call().id

    # topic = "machine learning"
    topics = ["AI agents", "agentic workflows"] 
    # topics = ["cs.AI", "cs.CL", "cs.DC"]
    select_prompt_file = "select_research_prompt.txt"
    question_prompt_file = "generate_questions_prompt.txt"
    summary_prompt_file = "summary_prompt.txt"
    editor_prompt_file = "editor_prompt.txt"
    # reference_files = ["article1.txt", "article2.txt", "article3.txt"]

    # Step 1: Get Arxiv possibilities
    print("Searching Arxiv...")
    possibilities = get_arxiv_possibilities(topics, max_results=20)
    print("Arxiv possibilities length:", len(possibilities))
    print("Arxiv possibilities type:", type(possibilities))
    print("Arxiv 1st possibility:", possibilities[0])

    # Step 2: Select the best papers
    # print("select_best_arxiv_papers:\n", await select_best_arxiv_papers(possibilities, select_prompt_file))
    pdf_urls, selected_titles, selection_call_id = await select_best_arxiv_papers(possibilities, select_prompt_file)
    if not pdf_urls:
        print("No papers selected.")
        return

    # List to keep track of downloaded PDF files
    downloaded_pdfs = []

    # Process each selected paper
    all_summaries = ""
    for pdf_url, selected_title in zip(pdf_urls, selected_titles):
        print(f"Selected Paper: {selected_title}")
        arxiv_url = pdf_url.replace("/pdf/", "/abs/").rstrip(".pdf")
        pdf_path = f"{pdf_url.split('/')[-1]}.pdf"
        os.system(f"curl -L {pdf_url} -o {pdf_path}")
        downloaded_pdfs.append(pdf_path)

        # Process this specific paper
        reference_text = read_reference_article(pdf_path)
        if not reference_text:
            print(f"Reference article {pdf_path} is missing or empty. Skipping...")
            continue

        # Extract content and generate questions
        paper_text = read_pdf_first_50_pages(pdf_path)
        if not paper_text.strip():
            print("Could not extract any text from the PDF.")
            continue
    
        print("Generating questions based on the paper content...")
        questions = await generate_questions_from_paper(paper_text, question_prompt_file)
        
        # Generate summary for this paper
        print(f"\n=== Generating Summary for {selected_title} ===")
        summary_output = await generate_summary_from_paper(paper_text, questions, summary_prompt_file, reference_text)

        print(f"Editing Summary for {selected_title}...")
        edited_summary = await edit_summary(summary_output, editor_prompt_file)

        all_summaries += f"=== Paper: {selected_title} ===\nArXiv URL: {arxiv_url}\n\n{edited_summary}\n\n"

    # Step 5: Email the summaries
    print("Sending email with summaries...")
    current_date = datetime.now().strftime("%Y-%m-%d")
    await send_email(
        subject=f"news_agent findings for {current_date} based on topics = {topics}",
        body=all_summaries,
        recipient_email=email,
        sender_email=email,
        sender_password=pswd,
        main_call_id=main_call_id,
        selection_call_id=selection_call_id
    )

    for pdf_file in downloaded_pdfs:
        try:
            os.remove(pdf_file)
            print(f"Deleted {pdf_file}")
        except Exception as e:
            print(f"Failed to delete {pdf_file}: {e}")


# Run the main function
asyncio.run(main())
