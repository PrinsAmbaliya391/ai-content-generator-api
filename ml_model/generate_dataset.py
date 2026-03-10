"""
Synthetic Dataset Generation Module.

This script generates a synthetic dataset for tone detection by sampling
predefined sentence templates for various emotional and professional tones.
The output is saved as 'tone_dataset.csv'.
"""

import pandas as pd
import random

# Seed for reproducibility
random.seed(42)

# Templates for various tones supported by the AI Content Generator
sentence_templates = {

"Professional":[
"Please review the attached report and provide your feedback.",
"The meeting has been scheduled for tomorrow morning.",
"Kindly ensure that all assigned tasks are completed on time.",
"Our team will continue monitoring the project progress closely.",
"Thank you for your professionalism and continued dedication.",
"Please contact the department if additional clarification is required.",
"We appreciate your cooperation regarding this matter.",
"The update has been shared with the management team.",
"Further information will be provided shortly.",
"Let us maintain clear and effective communication moving forward."
],

"Friendly":[
"Hi there! I hope you're having a wonderful day.",
"It was really nice talking with you earlier.",
"Let me know if you need anything, I'm happy to help.",
"Thanks for reaching out, I truly appreciate it.",
"I'm glad we could connect and work together.",
"Feel free to ask if you have any questions.",
"It’s always great chatting with you.",
"I hope everything is going well for you today.",
"Looking forward to hearing your thoughts.",
"Thanks again for your time and support."
],

"Casual":[
"Hey! Just wanted to check in with you.",
"No worries, we can sort this out easily.",
"Let's catch up later and talk about it.",
"Sounds good to me, let's move forward with it.",
"That's totally fine, take your time.",
"Just send me a message when you're free.",
"I'll take care of it later today.",
"It's all good, nothing to worry about.",
"Let me know what you think about it.",
"Alright, let's keep things simple."
],

"Polite":[
"Could you please share the required details?",
"I would greatly appreciate your assistance.",
"Thank you very much for your help.",
"Please let me know if I can assist further.",
"I sincerely appreciate your cooperation.",
"Kindly review the information provided.",
"Thank you for your patience and understanding.",
"I would be grateful for your response.",
"Please accept my sincere thanks.",
"I appreciate your time and consideration."
],

"Urgent":[
"This issue needs to be resolved immediately.",
"Please address this problem as soon as possible.",
"This matter requires urgent attention.",
"We need an immediate update on the situation.",
"The deadline is approaching very quickly.",
"Please prioritize this task right away.",
"This is a high-priority issue.",
"Immediate action is required.",
"Kindly respond as quickly as possible.",
"Time is critical for this request."
],

"Serious":[
"This matter requires careful consideration.",
"We must approach this situation responsibly.",
"The issue needs thorough evaluation.",
"This decision will have significant consequences.",
"We need to handle this situation with caution.",
"The matter is being reviewed seriously.",
"We must focus on resolving the problem.",
"This concern should not be ignored.",
"We must remain focused on the task ahead.",
"Responsible action is required."
],

"Rude":[
"This is completely unacceptable.",
"This work is terrible and poorly done.",
"This is a pathetic attempt at solving the problem.",
"This makes absolutely no sense.",
"This is one of the worst things I have seen.",
"This is badly executed work.",
"This result is extremely disappointing.",
"This is ridiculous and frustrating.",
"I expected far better than this.",
"This is simply awful work."
],

"Encouraging":[
"You are doing a great job, keep going.",
"Don't give up, you're making real progress.",
"I believe in your abilities.",
"You can definitely achieve this goal.",
"Keep pushing forward, success is close.",
"Your efforts are truly appreciated.",
"Stay positive and continue improving.",
"You have the potential to succeed.",
"Every step forward counts.",
"Great work so far, keep it up."
],

"Apologetic":[
"I'm truly sorry for the inconvenience caused.",
"Please accept my sincere apologies.",
"I regret the mistake that occurred.",
"We apologize for the delay in our response.",
"I'm sorry for any confusion this may have caused.",
"Thank you for your patience and understanding.",
"I deeply regret the issue that happened.",
"We sincerely apologize for the trouble caused.",
"I hope you can forgive this mistake.",
"Please allow us to correct the situation."
],

"Persuasive":[
"I strongly recommend considering this option.",
"This solution offers significant advantages.",
"You will benefit greatly from this decision.",
"This is the best approach moving forward.",
"Many people have successfully used this strategy.",
"I encourage you to take this opportunity.",
"This choice will lead to better results.",
"You should definitely give this a try.",
"This is a smart decision for the future.",
"I assure you this option will work well."
],

"Informative":[
"This report provides detailed information about the subject.",
"The following data explains the situation clearly.",
"Here are the important facts you should know.",
"This section outlines the key findings.",
"The information below explains the process.",
"This document contains useful insights.",
"These results are based on recent analysis.",
"The explanation will help clarify the issue.",
"This overview summarizes the main points.",
"The data supports the following conclusions."
],

"Neutral":[
"The meeting will take place tomorrow.",
"The report was submitted yesterday.",
"The system is currently operational.",
"The information has been recorded.",
"The update has been completed.",
"The request has been received.",
"The file has been uploaded.",
"The process has started.",
"The task has been assigned.",
"The results will be reviewed."
],

"Confident":[
"I am confident this plan will succeed.",
"We are fully prepared to handle this project.",
"Our strategy will deliver strong results.",
"This solution will work effectively.",
"We are ready to move forward.",
"I strongly believe this approach is correct.",
"Our team is capable of achieving this goal.",
"We have the expertise required.",
"This decision will lead to success.",
"We are certain about this direction."
]

}

def generate_content(tone, min_words=80):
    """
    Generates a synthetic content string for a given tone by sampling templates.

    Args:
        tone (str): The target sentiment or tone (e.g., 'Professional', 'Casual').
        min_words (int): The minimum word count for the generated content.

    Returns:
        str: A concatenated string of sentences matching the tone.
    """
    sentences = sentence_templates[tone]

    selected = random.sample(sentences, random.randint(7, 10))

    content = " ".join(selected)

    while len(content.split()) < min_words:
        content += " " + random.choice(sentences)

    return content


target_rows = 4500
tones = list(sentence_templates.keys())
rows_per_tone = target_rows // len(tones)

data = []

for tone in tones:
    for _ in range(rows_per_tone):
        data.append({
            "tone": tone,
            "content": generate_content(tone)
        })

while len(data) < target_rows:
    tone = random.choice(tones)
    data.append({
        "tone": tone,
        "content": generate_content(tone)
    })

random.shuffle(data)

df = pd.DataFrame(data)

df.to_csv("tone_dataset.csv", index=False)

print("Dataset created successfully!")
print("Total rows:", len(df))
print(df.head())