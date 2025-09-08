import re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide")
st.title("WhatsApp Chat Analysis Dashboard")

# ---------------- Regex for WhatsApp Chat ----------------
line_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{4}), (\d{2}:\d{2}) - (.+?): (.*)')

def parse_line(line):
    """Parse a single line of WhatsApp chat"""
    match = line_pattern.match(line)
    if match:
        date, time, name, message = match.groups()
        name = name.split('(')[0].strip()  # Clean names
        return [date, time, name, message]
    return None

def parse_chat(file):
    """Convert WhatsApp txt export to DataFrame"""
    data = []
    for raw_line in file:
        line = raw_line.decode("utf-8").strip()  # decode bytes to str
        parsed = parse_line(line)
        if parsed:
            data.append(parsed)
    df = pd.DataFrame(data, columns=["Date", "Time", "Name", "Message"])
    return df

# ---------------- Sidebar ----------------
st.sidebar.header("Upload WhatsApp Chat File")
uploaded_file = st.sidebar.file_uploader("Upload WhatsApp .txt", type=["txt"])

if uploaded_file:
    # Parse txt → DataFrame
    df = parse_chat(uploaded_file)

    # Convert Date + Time into datetime
    df['DateTime'] = pd.to_datetime(df['Date'] + " " + df['Time'], dayfirst=True, errors='coerce')
    df['Date'] = df['DateTime'].dt.date
    df['Time'] = df['DateTime'].dt.time
    df['HourRound'] = df['DateTime'].dt.hour
    df['MinuteRound'] = df['DateTime'].dt.floor('T')

    # ---------------- Sidebar Filters ----------------
    participants = df['Name'].unique().tolist()
    selected_participant = st.sidebar.multiselect("Select Participant(s)", options=participants, default=participants)
    
    min_date, max_date = df['Date'].min(), df['Date'].max()
    date_option = st.sidebar.radio("Select Date Option", ["All Dates", "Specific Date"])
    selected_date = st.sidebar.date_input("Select Date", min_value=min_date, max_value=max_date) if date_option == "Specific Date" else None
    
    keyword = st.sidebar.text_input("Search Messages (keyword)")

    # ---------------- Apply Filters ----------------
    filtered_df = df[df['Name'].isin(selected_participant)]
    if selected_date:
        filtered_df = filtered_df[filtered_df['Date'] == selected_date]
    if keyword:
        filtered_df = filtered_df[filtered_df['Message'].str.contains(keyword, case=False, na=False)]
    
    # ---------------- Show Raw Data ----------------
    st.subheader("Filtered Messages")
    st.dataframe(filtered_df[['Date', 'Time', 'Name', 'Message']])

    # ---------------- Chat Duration Summary ----------------
    st.subheader("Chat Duration Summary")
    duration_summary = []
    max_idle_minutes = 15  

    for participant in selected_participant:
        person_df = filtered_df[filtered_df['Name'] == participant].sort_values('DateTime')
        if not person_df.empty:
            total_duration = person_df['DateTime'].max() - person_df['DateTime'].min()
            total_hours, total_remainder = divmod(total_duration.total_seconds(), 3600)
            total_minutes, _ = divmod(total_remainder, 60)

            deltas = person_df['DateTime'].diff().fillna(pd.Timedelta(seconds=0))
            active_time = deltas[deltas <= pd.Timedelta(minutes=max_idle_minutes)].sum()
            active_hours, active_remainder = divmod(active_time.total_seconds(), 3600)
            active_minutes, _ = divmod(active_remainder, 60)

            duration_summary.append({
                'Participant': participant,
                'Messages Sent': person_df.shape[0],
                'Active Chat Duration': f"{int(active_hours)}h {int(active_minutes)}m"
            })

    st.dataframe(pd.DataFrame(duration_summary))

    # ---------------- Messages per Hour ----------------
    st.subheader("Messages per Hour per Participant")
    if not filtered_df.empty:
        hourly_counts = filtered_df.groupby(['HourRound', 'Name']).size().reset_index(name='MessageCount')
        fig_hourly = px.bar(
            hourly_counts,
            x="HourRound",
            y="MessageCount",
            color="Name",
            barmode="stack",
            title="Messages per Hour per Participant",
            labels={"HourRound": "Hour of Day", "MessageCount": "Number of Messages"}
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    # ---------------- Messages per Minute ----------------
    st.subheader("Messages per Minute per Participant")
    if not filtered_df.empty:
        minute_counts = filtered_df.groupby(['MinuteRound', 'Name']).size().reset_index(name='MessageCount')
        fig_minute = px.bar(
            minute_counts,
            x="MinuteRound",
            y="MessageCount",
            color="Name",
            barmode="stack",
            title="Messages per Minute per Participant",
            labels={"MinuteRound": "Time (Minute)", "MessageCount": "Number of Messages"}
        )
        st.plotly_chart(fig_minute, use_container_width=True)
