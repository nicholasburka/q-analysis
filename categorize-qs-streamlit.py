import requests
import csv
import json
import matplotlib.pyplot as plt
import anthropic
import numpy as np
import streamlit as st
import pandas as pd
from datetime import datetime


API_KEY = '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'
client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=API_KEY
)

def fetch_from_local_csv(file_path):
   with open(file_path, mode='r') as file:
       reader = csv.reader(file)
       data = [row for row in reader]  # Fetches all rows from the CSV file
   return data

def load_csv(uploaded_file):
    return pd.read_csv(uploaded_file).values.tolist()

def batch_all_qs(qs, batch_size=50):
    #data = get_csv(csv_path)
    #maybe dataframe
    q_index = 1
    #qs = data[q_index]
    batches = [[]]
    counter = 1
    batch_index = 0
    #break questions into batches for processing
    for i, q in enumerate(qs):
        if i > 0 and i % batch_size == 0:  # Check if we need a new batch
            batch_index += 1
            batches.append([])  # Create a new batch
        batches[batch_index].append(q)  # Add question to the current batch
    '''categorized_batches = []
    for batch in batches:
    categorized = categorize_qs(batch)
    categorized_batches.append(categorized)
    combine_batches(categorized_batches)'''
    return batches

def categorize_qs(q_batch, prev):
    #prompt = "I am reviewing the questions asked to a chatbot I maintain, that gives NYers information about how to get repairs in NYC apartments. Please categorize the questions from our users so I can quickly review them for semantic similarity. Please provide the number of questions within each category and sub-type, and the \"ID\"s (question number) associated. Please provide this output as a JSON object, with no non-JSON content. If questions fit into multiple categories, you can include them in multiple categories."
    prompt = "Please analyze these questions asked to a NYC apartment repairs chatbot and output a JSON object with the following strict structure: { 'categories': [ '[category_name]': { '[subtype_name]': [ { 'question_ids': number[] } ] } ] } The output should be a pure JSON object with no additional text or explanation. Question IDs should be zero-indexed. Questions can appear in multiple categories if relevant. If a previous JSON is provided, re-use the same category names as before if applicable for consistency, but ignore the question IDs (output a fresh JSON, rather than aggregating old question ID's with new)."
    prompt_with_qs = prompt + "\n\n Prev JSON:" + str(prev) + "\n\n New questions:" + str(q_batch)
    print(prompt_with_qs)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt_with_qs}
        ])
    return message, json.loads(message.content[0].text)

def categorize_batches(batches):
    batch_size = len(batches[0])
    categorized_total = {'categories': {}}
    for i, batch in enumerate(batches):
        print("Beginning batch number " + str(i + 1) + " of " + str(len(batches)))
        categorized_batch = categorize_qs(batch, categorized_total)[1] #gets the JSON from the response
        categorized_total = combine_json(categorized_total, categorized_batch, batch_size * i)
    return categorized_total

def combine_json(json1, json2, constant):
    combined_json = {'categories': {}}

    for category, subcategories in json2['categories'].items():
        if category not in combined_json['categories']:
            combined_json['categories'][category] = {}
        
        for subtype, questions in subcategories.items():
            if subtype not in combined_json['categories'][category]:
                combined_json['categories'][category][subtype] = [{'question_ids': []}]
            
            # Append modified question IDs
            modified_ids = [qid + constant for qid in questions[0]['question_ids']]
            combined_json['categories'][category][subtype][0]['question_ids'].extend(modified_ids)

    # Now, also add the existing categories from json1
    for category, subcategories in json1['categories'].items():
        if category not in combined_json['categories']:
            combined_json['categories'][category] = subcategories
        else:
            for subtype, questions in subcategories.items():
                if subtype not in combined_json['categories'][category]:
                    combined_json['categories'][category][subtype] = questions
                else:
                    combined_json['categories'][category][subtype][0]['question_ids'].extend(questions[0]['question_ids'])

    return combined_json

def total_questions(json_data):
    total_count = 0
    
    # Iterate through the categories
    for category, subcategories in json_data['categories'].items():
        # Iterate through the subcategories
        for subtype, questions in subcategories.items():
            # Sum the number of question IDs in each subtype
            total_count += len(questions[0]['question_ids'])
    
    return total_count

def make_cat_bar_chart(data, qs, streamlit=False):
    categories = list(data['categories'].keys())
    subcategories = []
    counts = []
    cat_questions = []
    for category in categories:
        for subcategory, questions in data['categories'][category].items():
            subcategories.append(f"{category} - {subcategory}")
            counts.append(len(questions[0]['question_ids']))
    for category in categories:
        for subcategory, questions in data['categories'][category].items():
            for question_list in questions:
                for q in question_list['question_ids']:
                    print(q)
                    print(len(qs))
                    print(qs)
                    cat_questions.append(f"{category} - {subcategory}: " + qs[q])
    
    # Set the width of each bar
    bar_width = 0.4
    
    # Create positions with spacers between categories
    spacer = 0.8  # Increase this value for more space between categories
    current_position = 0
    grouped_positions = []
    current_category = None
    
    for i, subcategory in enumerate(subcategories):
        category = subcategory.split(' - ')[0]
        
        # Add spacer when switching to new category
        if current_category is not None and category != current_category:
            current_position += spacer
        
        grouped_positions.append(current_position)
        current_position += 1
        current_category = category
    
    # Create the bar chart
    plt.figure(figsize=(12, 6))  # Adjust figure size to accommodate spacers
    plt.bar(grouped_positions, counts, width=bar_width, color='skyblue', edgecolor='grey')
    
    # Add labels and title
    plt.xlabel('Subcategories', fontweight='bold')
    plt.ylabel('Number of Questions', fontweight='bold')
    plt.title('Grouped Bar Chart of Questions by Subcategory')
    
    # Set x-ticks to the center of the groups
    plt.xticks(grouped_positions, subcategories, rotation=45, ha='right')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    if (not streamlit):
        plt.show()
    else:
        #return plt
        #print("st")
        st.pyplot(plt)
    return cat_questions#, plt

def analyze_qs_local(csv_filepath, q_row_index=1, batch_size=50):
    data = fetch_from_csv(csv_filepath)
    qs = list(map(lambda row: row[q_row_index], data))
    batches = batch_all_qs(qs, batch_size)
    categorized_batches = categorize_batches(batches)
    categorized_qs = make_cat_bar_chart(categorized_batches, qs)

def analyze_qs_st(data, q_row_index=1, batch_size=50):
    qs = [row[1] for row in data]
    batches = batch_all_qs(qs, batch_size)
    categorized_batches = categorize_batches(batches)
    categorized_qs = make_cat_bar_chart(categorized_batches, qs, True)
    #q_cats = [q.split(':')[0] for q in categorized_qs]
    orig = pd.DataFrame(data, columns=['ID', 'Question', 'Answer', 'Date created', 'Date last modified', 'Positive feedback', 'Negative feedback', 'Moderated/Unmoderated', 'Active/Inactive'])
    cats = pd.DataFrame([q.split(': ') for q in categorized_qs], columns=["Categories", "Question"])
    #cats = cats.iloc[:, :-2]
    cats_agg = cats.groupby('Question', as_index=False).agg({
        'Categories': lambda q: ', '.join(q.unique())  # Combine categories by comma
        })
    merged_df = pd.merge(cats_agg, orig, on='Question', how='left')
    #df['Question Category'] = q_cats
    #categorized_qs, cat_chart = make_cat_bar_chart(categorized_batches, qs, True)
    return categorized_batches, categorized_qs, merged_df
    '''st.subheader("Categorized Questions")
    for q in categorized_qs:
        st.write(q)'''

#analyze_qs('hca-min.csv', 1, 10)

def main():
    st.title("Analyze your Josef Q CSV")
    st.subheader("Understand what users are asking")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    #st.subheader("-------")
    #uploaded_prev = st.file_uploader("Upload a prev analyzed file", type=["csv"])
    if (uploaded_file is not None):
        # Fetch data from the uploaded CSV
        data = load_csv(uploaded_file)
        qs = [row[1] for row in data]

        if 'categorized_qs' not in st.session_state:
            st.subheader("Analyzing data...")
            categorized_batches, categorized_qs, data = analyze_qs_st(data)
            st.session_state.categorized_batches = categorized_batches
            st.session_state.categorized_qs = categorized_qs
            st.session_state.modified_data = data
            st.session_state.mod_csv = data.to_csv(index=False)
            #st.session_state.cat_chart = cat_chart
        else:
            categorized_batches = st.session_state.categorized_batches
            categorized_qs = st.session_state.categorized_qs
            modified_data = st.session_state.modified_data
            mod_csv = st.session_state.mod_csv
            #cat_chart = st.session_state.cat_chart
            make_cat_bar_chart(categorized_batches, qs, True)

        #st.pyplot(cat_chart)
        # Get the current date and time
        current_time = datetime.now()
        # Format the date and time as a string
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        st.download_button("Download the categorized CSV", st.session_state.mod_csv, timestamp + "_categorized_josefQ_questions.csv", "text/csv")
        selected_category = st.selectbox("Select a category to see questions:", list(categorized_batches['categories'].keys()))

        if selected_category:
            st.subheader(f"Questions in **{selected_category}**:")
            filtered_qs = filter(lambda q: q[0: len(selected_category)] == selected_category, categorized_qs)
            for question in filtered_qs:
                st.write(f"- {question}")


if __name__ == "__main__":
    main()