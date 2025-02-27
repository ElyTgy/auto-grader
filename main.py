from autograder.box_extractor import box_extraction
from autograder.character_predictor import predict
from autograder.spelling_corrector import fix_spellings
from autograder.text_similarity import check_similarity, get_marks

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from typing import List
import numpy as np
import cv2

app = FastAPI(
    title="Auto-Grader",
    version="1.0",
    description="Automatically grades answer sheets",
)


def auto_grade(defined_answers, img, max_marks, bias):
    answers, coordinates = box_extraction(img)
    if len(answers) == 380:

        locations = []
        prev = 0
        print(
            answers.shape
        )  # 16 cells x 2 rows x 10 answers = 360 boxes x (28 x 28) pixels

        marks = []

        for n in range(10):  # all questions
            sentence = ""
            answer = answers[38 * n : 38 * (n + 1)]  # individual answer(2 rows)
            for i in range(38):  # boxes of a answer
                box = answer[i]
                sum_pix = 0
                for pixel in box:  #  pixel of the box
                    if pixel != 0:
                        sum_pix = sum_pix + 1
                # do nothing when char is detected in the box, counter i will increase. When and empty
                # box is detected after some character boxes, pix < 30
                if sum_pix < 30 or i == 37:
                    word_array = answer[prev:i].reshape(-1, 28, 28, 1)
                    if word_array.shape[0] > 1:
                        try:
                            pred = predict(word_array)
                            if i < 16:
                                sentence = sentence + "".join(pred) + " "
                            else:
                                sentence = "".join(pred) + " " + sentence
                        except:
                            print(word_array.shape)
                    prev = i + 1

            print(n + 1, sentence[::-1])

            new_words = []
            for answer in defined_answers[n]:
                words = answer.split()
                for word in words:
                    new_words.append(word.lower())

            query = fix_spellings(sentence[::-1].lower(), new_words)

            if query != "":
                print(query)
                cos_scores = check_similarity(defined_answers[n], query)
                m = get_marks(cos_scores, max_marks, bias)
                print("Marks: ", "%.2f" % m)
                marks.append(round(m, 4))
            else:
                print("Marks: ", "0.00")
                marks.append(0.0)
        return marks


@app.get("/")
async def index():
    return {"message": "Auto-Grader is online"}


@app.post("/grade/")
async def index(
    ans1: List[str],
    ans2: List[str],
    ans3: List[str],
    ans4: List[str],
    ans5: List[str],
    ans6: List[str],
    ans7: List[str],
    ans8: List[str],
    ans9: List[str],
    ans10: List[str],
    max_marks: float,
    lower_limit: float,
    upper_limit: float,
    file: UploadFile = File(...),
):
    if lower_limit > 1.0 or lower_limit < 0.0 or upper_limit > 1.0 or upper_limit < 0.0:
        raise HTTPException(status_code=400, detail="bias1 or bias2 not in range (0-1)")
    if lower_limit > upper_limit:
        raise HTTPException(
            status_code=400, detail="lower_limit cannot be greater than upper_limit"
        )
    extension = file.filename.split(".")[-1] in ("jpg", "jpeg", "png", "JPG", "PNG")
    if not extension:
        raise HTTPException(
            status_code=400, detail="File must be an image, in jpg or png format!"
        )

    image = await file.read()
    nparr = np.fromstring(image, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    ans_list = [
        ans1,
        ans2,
        ans3,
        ans4,
        ans5,
        ans6,
        ans7,
        ans8,
        ans9,
        ans10,
    ]
    marks = auto_grade(ans_list, img, max_marks, (lower_limit, upper_limit))
    return {"marks": marks}
