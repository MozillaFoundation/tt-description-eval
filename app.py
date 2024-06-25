import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_ID = st.secrets.sheet_id

TT_URL_FORMAT = "https://www.tiktok.com/@doesnotmatter/video/{vid}"

st.set_page_config(layout="wide")


@st.cache_resource
def get_sheets():
    creds = Credentials.from_service_account_info(
        st.secrets.service_account, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    descriptions_sheet = client.open_by_key(SHEET_ID).worksheet("descriptions")
    ratings_sheet = client.open_by_key(SHEET_ID).worksheet("ratings")
    return descriptions_sheet, ratings_sheet


if "ready_to_submit" not in st.session_state:
    st.session_state["ready_to_submit"] = False


descriptions_sheet, ratings_sheet = get_sheets()


def get_new_video():
    data = descriptions_sheet.get_all_records()
    data_df = pd.DataFrame(data)
    unique_video_paths = data_df["video_path"].unique()
    random_video_path = np.random.choice(unique_video_paths)
    video_id = random_video_path.split("/")[-1].split(".")[0]
    descriptions_data = data_df.loc[
        data_df["video_path"] == random_video_path,
        ["model", "description", "video_path"],
    ]
    st.session_state["cur_data"] = None
    return video_id, descriptions_data


def handle_submit():
    for _, row in st.session_state["cur_data"].iterrows():
        row_values = row.values.flatten().tolist()
        row_values.append(st.session_state["name"])
        ratings_sheet.append_row(row_values)
    st.session_state["current_video"] = None


def ready_to_submit():
    quality_values = st.session_state["cur_data"]["quality"].values
    return st.session_state["name"] != "" and all(
        value.isdigit() and 1 <= int(value) <= 5 for value in quality_values
    )


def name_changed():
    st.session_state["ready_to_submit"] = ready_to_submit()


def data_changed():
    state = st.session_state["df_editor"]
    for index, updates in state["edited_rows"].items():
        for key, value in updates.items():
            st.session_state["cur_data"].loc[
                st.session_state["cur_data"].index == index, key
            ] = value
    st.session_state["ready_to_submit"] = ready_to_submit()


st.title("Description Eval Tool")

st.text_input("Your name", key="name", on_change=name_changed)

if ("current_video" not in st.session_state) or (
    st.session_state["current_video"] is None
):
    st.session_state["current_video"] = get_new_video()
video_id, descriptions_data = st.session_state["current_video"]
st.write(f"TikTok to evaluate: {TT_URL_FORMAT.format(vid=video_id)}")


col1, col2 = st.columns([3, 1])
if st.session_state["cur_data"] is None:
    descriptions_data["quality"] = ""
    st.session_state["cur_data"] = descriptions_data.reset_index(drop=True)

col1.data_editor(
    st.session_state["cur_data"],
    column_config={"model": None, "video_path": None},
    disabled=["description"],
    hide_index=True,
    on_change=data_changed,
    key="df_editor",
)


col2.markdown(
    """## Please double click each description to read the full text

Description of what rating values mean:
 - 1: bad
 - 2 better..."""
)

st.button(
    "submit",
    on_click=handle_submit,
    disabled=not st.session_state["ready_to_submit"]
)
st.button(
    "skip",
    on_click=lambda: st.session_state.update({"current_video": None})
)
