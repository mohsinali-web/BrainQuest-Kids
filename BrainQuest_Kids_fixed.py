import streamlit as st
import sqlite3
import random
import time
from datetime import datetime, date, timedelta

import pandas as pd
import plotly.express as px


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BrainQuest Kids",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "brainquest.db"
PARENT_PIN = "1234"  # Change this before using the app.


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            stars INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            task_date TEXT,
            task_id TEXT,
            task_name TEXT,
            completed INTEGER DEFAULT 0,
            reward INTEGER DEFAULT 0,
            UNIQUE(child_id, task_date, task_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            played_at TEXT,
            game TEXT,
            category TEXT,
            level INTEGER,
            score INTEGER,
            accuracy REAL,
            time_taken REAL
        )
    """)

    conn.commit()
    conn.close()


init_database()


# ============================================================
# TASK DATA
# ============================================================

TASKS = [
    {
        "id": "water",
        "name": "Drink Water",
        "icon": "💧",
        "reward": 5,
    },
    {
        "id": "brush",
        "name": "Brush Your Teeth",
        "icon": "🪥",
        "reward": 5,
    },
    {
        "id": "clothes",
        "name": "Fold / Put Away Clothes",
        "icon": "👕",
        "reward": 10,
    },
    {
        "id": "room",
        "name": "Help Clean Your Room",
        "icon": "🧹",
        "reward": 15,
    },
    {
        "id": "study",
        "name": "Study / Read for 30 Minutes",
        "icon": "📚",
        "reward": 20,
    },
    {
        "id": "toys",
        "name": "Put Toys / Items Away",
        "icon": "🧸",
        "reward": 10,
    },
    {
        "id": "movement",
        "name": "Do a Short Movement Activity",
        "icon": "🏃",
        "reward": 10,
    },
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def today_string():
    return date.today().isoformat()


def yesterday_string():
    return (date.today() - timedelta(days=1)).isoformat()


def get_child(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM children WHERE name = ?",
        (name,),
    )

    result = cursor.fetchone()
    conn.close()
    return result


def create_child(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO children
        (name, stars, xp, streak, last_active)
        VALUES (?, 0, 0, 0, ?)
        """,
        (name, today_string()),
    )

    conn.commit()
    conn.close()


def update_child(child_id, stars=0, xp=0):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE children
        SET stars = stars + ?,
            xp = xp + ?,
            last_active = ?
        WHERE id = ?
        """,
        (
            stars,
            xp,
            today_string(),
            child_id,
        ),
    )

    conn.commit()
    conn.close()


def update_streak(child_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT streak, last_active
        FROM children
        WHERE id = ?
        """,
        (child_id,),
    )

    result = cursor.fetchone()

    if result is None:
        conn.close()
        return

    current_streak, last_active = result
    today = today_string()
    yesterday = yesterday_string()

    if last_active == today:
        new_streak = current_streak
    elif last_active == yesterday:
        new_streak = current_streak + 1
    else:
        new_streak = 1

    cursor.execute(
        """
        UPDATE children
        SET streak = ?, last_active = ?
        WHERE id = ?
        """,
        (new_streak, today, child_id),
    )

    conn.commit()
    conn.close()


def get_child_stats(child_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name, stars, xp, streak, last_active
        FROM children
        WHERE id = ?
        """,
        (child_id,),
    )

    result = cursor.fetchone()
    conn.close()
    return result


def get_level(xp):
    return max(1, (xp // 100) + 1)


def level_progress(xp):
    return (xp % 100) / 100


# ============================================================
# TASK FUNCTIONS
# ============================================================

def create_today_tasks(child_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = today_string()

    for task in TASKS:
        cursor.execute(
            """
            INSERT OR IGNORE INTO tasks
            (child_id, task_date, task_id, task_name, completed, reward)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                child_id,
                today,
                task["id"],
                task["name"],
                task["reward"],
            ),
        )

    conn.commit()
    conn.close()


def get_today_tasks(child_id):
    create_today_tasks(child_id)

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM tasks
        WHERE child_id = ?
        AND task_date = ?
        ORDER BY id
        """,
        conn,
        params=(child_id, today_string()),
    )

    conn.close()
    return df


def complete_task(child_id, task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT completed, reward
        FROM tasks
        WHERE child_id = ?
        AND task_date = ?
        AND task_id = ?
        """,
        (
            child_id,
            today_string(),
            task_id,
        ),
    )

    result = cursor.fetchone()

    if result is None:
        conn.close()
        return False, 0

    completed, reward = result

    if completed == 1:
        conn.close()
        return False, 0

    cursor.execute(
        """
        UPDATE tasks
        SET completed = 1
        WHERE child_id = ?
        AND task_date = ?
        AND task_id = ?
        """,
        (
            child_id,
            today_string(),
            task_id,
        ),
    )

    conn.commit()
    conn.close()

    update_child(
        child_id,
        stars=reward,
        xp=reward,
    )

    update_streak(child_id)

    return True, reward


# ============================================================
# GAME DATABASE
# ============================================================

def save_game_score(
    child_id,
    game,
    category,
    level,
    score,
    accuracy,
    time_taken,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO game_scores
        (
            child_id,
            played_at,
            game,
            category,
            level,
            score,
            accuracy,
            time_taken
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            child_id,
            datetime.now().isoformat(timespec="seconds"),
            game,
            category,
            level,
            int(score),
            float(accuracy),
            float(time_taken),
        ),
    )

    conn.commit()
    conn.close()


def get_game_scores(child_id):
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM game_scores
        WHERE child_id = ?
        ORDER BY played_at
        """,
        conn,
        params=(child_id,),
    )

    conn.close()
    return df


def get_average_score(child_id, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT AVG(score)
        FROM game_scores
        WHERE child_id = ?
        AND category = ?
        """,
        (
            child_id,
            category,
        ),
    )

    result = cursor.fetchone()[0]
    conn.close()

    return round(result or 0, 1)


def award_game_xp(child_id, score):
    # Small game reward without allowing very large XP jumps.
    xp_reward = max(5, min(25, int(score / 5)))
    update_child(child_id, xp=xp_reward)
    return xp_reward


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "game": None,
    "game_data": {},
    "game_start": None,
    "game_finished": False,
    "game_saved": False,
    "message": "",
    "parent_authenticated": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_game():
    st.session_state.game = None
    st.session_state.game_data = {}
    st.session_state.game_start = None
    st.session_state.game_finished = False
    st.session_state.game_saved = False


def finish_game(
    child_id,
    game_name,
    category,
    level,
    score,
    accuracy,
    elapsed,
):
    if st.session_state.game_saved:
        return

    save_game_score(
        child_id,
        game_name,
        category,
        level,
        score,
        accuracy,
        elapsed,
    )

    xp_reward = award_game_xp(child_id, score)

    st.session_state.game_saved = True
    st.session_state.game_finished = True
    st.session_state.game_data["final_score"] = score
    st.session_state.game_data["final_accuracy"] = accuracy
    st.session_state.game_data["final_time"] = elapsed
    st.session_state.game_data["xp_reward"] = xp_reward


def games_unlocked(child_id):
    df = get_today_tasks(child_id)
    return not df.empty and int(df["completed"].sum()) > 0


# ============================================================
# CHILD LOGIN / PROFILE
# ============================================================

st.sidebar.title("🧠 BrainQuest")

st.sidebar.markdown("### Who is playing?")

name = st.sidebar.text_input(
    "Child name",
    value="Alex",
).strip()

if not name:
    st.warning("Please enter a child name.")
    st.stop()

create_child(name)
child = get_child(name)

if child is None:
    st.error("Unable to create the child profile.")
    st.stop()

child_id = child[0]
stats = get_child_stats(child_id)

child_name = stats[0]
stars = stats[1]
xp = stats[2]
streak = stats[3]

level = get_level(xp)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Home",
        "✅ Daily Tasks",
        "🎮 Brain Games",
        "📊 Progress",
        "👨‍👩‍👧 Parent View",
    ],
)


# ============================================================
# HEADER
# ============================================================

st.title("🧠 BrainQuest Kids")

st.caption(
    "Complete everyday responsibilities, earn stars, "
    "and enjoy short brain-training activities."
)


# ============================================================
# HOME
# ============================================================

if page == "🏠 Home":
    st.subheader(f"Welcome, {child_name}! 👋")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("⭐ Stars", stars)
    col2.metric("🧠 Brain Level", level)
    col3.metric("🔥 Streak", streak)
    col4.metric(
        "🎮 Games Played",
        len(get_game_scores(child_id)),
    )

    st.divider()

    st.subheader("Today's Mission 🌞")

    task_df = get_today_tasks(child_id)

    completed = int(task_df["completed"].sum())
    total = len(task_df)
    progress = completed / total if total else 0

    st.progress(progress)

    st.write(f"**{completed} of {total} tasks completed**")

    for _, task in task_df.iterrows():
        if task["completed"]:
            st.success(
                f"✅ {task['task_name']} "
                f"+{task['reward']} ⭐"
            )
        else:
            st.info(
                f"⬜ {task['task_name']} "
                f"+{task['reward']} ⭐"
            )

    st.divider()

    st.subheader("🧠 Brain Level")

    st.progress(level_progress(xp))

    st.write(
        f"Level {level} — "
        f"{xp % 100}/100 XP toward next level"
    )

    if completed == total and total > 0:
        st.balloons()
        st.success("🎉 Amazing! Today's mission is complete!")

    st.divider()

    st.subheader("🎮 What can you play?")

    if completed > 0:
        st.success("🎮 Brain games unlocked!")
    else:
        st.warning("Complete a task first to unlock games.")


# ============================================================
# DAILY TASKS
# ============================================================

elif page == "✅ Daily Tasks":
    st.header("🌞 Daily Tasks")

    st.write(
        "Finish your normal responsibilities and earn stars."
    )

    task_df = get_today_tasks(child_id)

    for _, task in task_df.iterrows():
        col1, col2, col3 = st.columns([5, 2, 2])

        with col1:
            if task["completed"]:
                st.markdown(
                    f"### ✅ {task['task_name']}"
                )
            else:
                st.markdown(
                    f"### {task['task_name']}"
                )

        with col2:
            st.write(f"⭐ +{task['reward']}")

        with col3:
            if task["completed"]:
                st.button(
                    "Completed ✓",
                    disabled=True,
                    key=f"done_{task['task_id']}",
                )
            else:
                if st.button(
                    "Complete",
                    key=f"complete_{task['task_id']}",
                ):
                    success, reward = complete_task(
                        child_id,
                        task["task_id"],
                    )

                    if success:
                        st.success(
                            f"Great job! +{reward} ⭐"
                        )
                    else:
                        st.info("This task was already completed.")

                    st.rerun()

        st.divider()


# ============================================================
# GAME MENU
# ============================================================

elif page == "🎮 Brain Games":
    st.header("🎮 Brain Games")

    if not games_unlocked(child_id):
        st.warning(
            "🔒 Complete at least one daily task "
            "before playing a brain game."
        )
        st.info(
            "Go to **Daily Tasks** to begin today's mission."
        )
        st.stop()

    st.success("🎉 Games unlocked!")

    # --------------------------------------------------------
    # NO ACTIVE GAME
    # --------------------------------------------------------

    if st.session_state.game is None:
        st.write("Choose a short brain challenge:")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("## 🎈")
            st.subheader("Pop Balloons")
            st.write("Reaction speed and attention.")

            if st.button("Play", key="balloon_start"):
                reset_game()
                st.session_state.game = "balloon"
                st.session_state.game_data = {
                    "score": 0,
                    "balloons": [],
                    "remaining": [],
                }
                st.session_state.game_start = time.time()
                st.rerun()

        with col2:
            st.markdown("## 👀")
            st.subheader("Odd One Out")
            st.write("Visual attention and discrimination.")

            if st.button("Play", key="odd_start"):
                reset_game()
                st.session_state.game = "odd"
                st.session_state.game_data = {}
                st.session_state.game_start = time.time()
                st.rerun()

        with col3:
            st.markdown("## 🧠")
            st.subheader("Memory Match")
            st.write("Working memory and recall.")

            if st.button("Play", key="memory_start"):
                reset_game()
                st.session_state.game = "memory"
                st.session_state.game_data = {}
                st.session_state.game_start = time.time()
                st.rerun()

        col4, col5, col6 = st.columns(3)

        with col4:
            st.markdown("## 🔢")
            st.subheader("Number Sequence")
            st.write("Pattern recognition and reasoning.")

            if st.button("Play", key="sequence_start"):
                reset_game()
                st.session_state.game = "sequence"
                st.session_state.game_data = {}
                st.session_state.game_start = time.time()
                st.rerun()

        with col5:
            st.markdown("## 🧩")
            st.subheader("Pattern Puzzle")
            st.write("Logic and visual reasoning.")

            if st.button("Play", key="pattern_start"):
                reset_game()
                st.session_state.game = "pattern"
                st.session_state.game_data = {}
                st.session_state.game_start = time.time()
                st.rerun()

        with col6:
            st.markdown("## ⚡")
            st.subheader("Reaction Challenge")
            st.write("Quick responses and attention.")

            if st.button("Play", key="reaction_start"):
                reset_game()
                st.session_state.game = "reaction"
                st.session_state.game_data = {}
                st.session_state.game_start = time.time()
                st.rerun()

    # ========================================================
    # BALLOON GAME
    # ========================================================

    elif st.session_state.game == "balloon":
        st.subheader("🎈 Pop Balloons")
        st.write("Pop as many balloons as you can!")

        data = st.session_state.game_data

        if not data["balloons"]:
            balloons = [
                f"🎈 {i + 1}"
                for i in range(12)
            ]
            random.shuffle(balloons)

            data["balloons"] = balloons
            data["remaining"] = balloons.copy()

        score = data["score"]
        st.metric("Score", score)

        if data["remaining"]:
            cols = st.columns(4)

            for i, balloon in enumerate(data["remaining"]):
                with cols[i % 4]:
                    if st.button(
                        balloon,
                        key=f"balloon_{balloon}",
                    ):
                        data["score"] += 10
                        data["remaining"].remove(balloon)
                        st.rerun()
        else:
            elapsed = time.time() - st.session_state.game_start

            finish_game(
                child_id,
                "Pop Balloons",
                "Reaction",
                level,
                data["score"],
                100,
                elapsed,
            )

            st.success(
                f"🎉 Great job! You scored {data['score']} points."
            )
            st.write(
                f"Time: {data['final_time']:.1f} seconds"
            )
            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button("Back to Games", key="balloon_back"):
                reset_game()
                st.rerun()

    # ========================================================
    # ODD ONE OUT
    # ========================================================

    elif st.session_state.game == "odd":
        st.subheader("👀 Odd One Out")

        data = st.session_state.game_data

        if "odd" not in data:
            grid_size = min(3 + level, 7)
            total = grid_size ** 2

            data["grid_size"] = grid_size
            data["odd"] = random.randrange(total)
            data["shape"] = random.choice(
                ["🔵", "🟢", "🟡", "🔴"]
            )

            data["different"] = random.choice(
                ["🔷", "🟩", "⭐", "❤️"]
            )

        if data.get("answered", False):
            st.success(
                "🎯 Correct!"
                if data["correct"]
                else "Not quite! Try again next time."
            )

            st.metric(
                "Score",
                data["final_score"],
            )

            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button("Back to Games", key="odd_back"):
                reset_game()
                st.rerun()

        else:
            grid_size = data["grid_size"]
            total = grid_size ** 2

            st.write(
                "Find the one item that is different."
            )

            cols = st.columns(grid_size)

            for i in range(total):
                with cols[i % grid_size]:
                    if i == data["odd"]:
                        label = data["different"]
                    else:
                        label = data["shape"]

                    if st.button(
                        label,
                        key=f"odd_{i}",
                    ):
                        elapsed = (
                            time.time()
                            - st.session_state.game_start
                        )

                        correct = i == data["odd"]
                        score = 100 if correct else 20
                        accuracy = 100 if correct else 20

                        data["answered"] = True
                        data["correct"] = correct

                        finish_game(
                            child_id,
                            "Odd One Out",
                            "Attention",
                            level,
                            score,
                            accuracy,
                            elapsed,
                        )

                        st.rerun()

    # ========================================================
    # MEMORY GAME
    # ========================================================

    elif st.session_state.game == "memory":
        st.subheader("🧠 Memory Match")

        data = st.session_state.game_data

        if "cards" not in data:
            symbols = [
                "🍎",
                "🚗",
                "🐶",
                "⭐",
                "🌈",
                "🍕",
                "🚀",
                "🐱",
            ]

            pairs = symbols[:4]
            cards = pairs + pairs
            random.shuffle(cards)

            data["cards"] = cards
            data["revealed"] = []
            data["matched"] = []
            data["moves"] = 0
            data["mismatch"] = None

        cards = data["cards"]
        revealed = data["revealed"]
        matched = data["matched"]

        if data.get("finished", False):
            elapsed = data["final_time"]

            st.success(
                f"🎉 You matched everything! "
                f"Score: {data['final_score']}"
            )
            st.write(
                f"Moves: {data['moves']} | "
                f"Time: {elapsed:.1f} seconds"
            )
            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button("Back to Games", key="memory_back"):
                reset_game()
                st.rerun()

        elif data.get("mismatch") is not None:
            first, second = data["mismatch"]

            st.warning(
                "Those cards do not match. "
                "Click the button to continue."
            )

            if st.button("Continue", key="memory_continue"):
                revealed.clear()
                data["mismatch"] = None
                st.rerun()

        else:
            cols = st.columns(4)

            for i, symbol in enumerate(cards):
                with cols[i % 4]:
                    if i in revealed or i in matched:
                        label = symbol
                    else:
                        label = "❓"

                    if st.button(
                        label,
                        key=f"memory_{i}",
                    ):
                        if (
                            i not in revealed
                            and i not in matched
                            and len(revealed) < 2
                        ):
                            revealed.append(i)

                            if len(revealed) == 2:
                                data["moves"] += 1

                                first = revealed[0]
                                second = revealed[1]

                                if cards[first] == cards[second]:
                                    matched.extend(
                                        [first, second]
                                    )
                                    revealed.clear()

                                    if len(matched) == len(cards):
                                        elapsed = (
                                            time.time()
                                            - st.session_state.game_start
                                        )

                                        score = max(
                                            20,
                                            120 - data["moves"] * 10,
                                        )

                                        finish_game(
                                            child_id,
                                            "Memory Match",
                                            "Memory",
                                            level,
                                            score,
                                            100,
                                            elapsed,
                                        )

                                        data["finished"] = True
                                else:
                                    data["mismatch"] = (
                                        first,
                                        second,
                                    )

                            st.rerun()

            st.write(f"Moves: {data['moves']}")

    # ========================================================
    # NUMBER SEQUENCE
    # ========================================================

    elif st.session_state.game == "sequence":
        st.subheader("🔢 Number Sequence")

        data = st.session_state.game_data

        if "sequence" not in data:
            start = random.randint(1, 10)
            step = random.randint(2, 6)

            sequence = [
                start + step * i
                for i in range(4)
            ]

            answer = sequence[-1] + step

            choices = [
                answer,
                answer + random.choice([-3, -2, 2, 3]),
                answer + random.choice([-5, 4, 5, 6]),
                answer + random.choice([-7, 7, 8, 9]),
            ]

            choices = list(dict.fromkeys(choices))

            while len(choices) < 4:
                candidate = answer + random.randint(-10, 10)
                if candidate not in choices and candidate != answer:
                    choices.append(candidate)

            random.shuffle(choices)

            data["sequence"] = sequence
            data["answer"] = answer
            data["choices"] = choices

        if data.get("answered", False):
            st.success(
                "🎯 Correct!"
                if data["correct"]
                else f"The answer was {data['answer']}."
            )

            st.metric(
                "Score",
                data["final_score"],
            )

            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button(
                "Back to Games",
                key="sequence_back",
            ):
                reset_game()
                st.rerun()

        else:
            sequence = data["sequence"]

            st.markdown("### What number comes next?")

            st.markdown(
                "## "
                + "   →   ".join(
                    str(x)
                    for x in sequence
                )
                + "   →   ❓"
            )

            for index, choice in enumerate(data["choices"]):
                if st.button(
                    str(choice),
                    key=f"seq_{index}_{choice}",
                ):
                    elapsed = (
                        time.time()
                        - st.session_state.game_start
                    )

                    correct = choice == data["answer"]
                    score = 100 if correct else 20

                    data["answered"] = True
                    data["correct"] = correct

                    finish_game(
                        child_id,
                        "Number Sequence",
                        "Reasoning",
                        level,
                        score,
                        100 if correct else 20,
                        elapsed,
                    )

                    st.rerun()

    # ========================================================
    # PATTERN PUZZLE
    # ========================================================

    elif st.session_state.game == "pattern":
        st.subheader("🧩 Pattern Puzzle")

        data = st.session_state.game_data

        if "pattern" not in data:
            patterns = [
                (
                    ["🔵", "🔴", "🔵", "🔴"],
                    "🔵",
                ),
                (
                    ["⭐", "🌙", "⭐", "🌙"],
                    "⭐",
                ),
                (
                    ["🟢", "🟢", "🟡", "🟢", "🟢"],
                    "🟡",
                ),
                (
                    ["🍎", "🍌", "🍎", "🍌"],
                    "🍎",
                ),
            ]

            pattern, answer = random.choice(patterns)

            options = [
                answer,
                "🔵",
                "🔴",
                "⭐",
                "🌙",
                "🍎",
                "🍌",
                "🟢",
                "🟡",
            ]

            options = list(dict.fromkeys(options))
            random.shuffle(options)

            data["pattern"] = pattern
            data["answer"] = answer
            data["options"] = options

        if data.get("answered", False):
            st.success(
                "🎯 Correct!"
                if data["correct"]
                else f"The correct answer was {data['answer']}."
            )

            st.metric(
                "Score",
                data["final_score"],
            )

            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button(
                "Back to Games",
                key="pattern_back",
            ):
                reset_game()
                st.rerun()

        else:
            st.markdown("### Find the next item:")

            st.markdown(
                "## "
                + "   ".join(data["pattern"])
                + "   ❓"
            )

            for index, option in enumerate(data["options"]):
                if st.button(
                    option,
                    key=f"pattern_{index}_{option}",
                ):
                    elapsed = (
                        time.time()
                        - st.session_state.game_start
                    )

                    correct = option == data["answer"]
                    score = 100 if correct else 20

                    data["answered"] = True
                    data["correct"] = correct

                    finish_game(
                        child_id,
                        "Pattern Puzzle",
                        "Reasoning",
                        level,
                        score,
                        100 if correct else 20,
                        elapsed,
                    )

                    st.rerun()

    # ========================================================
    # REACTION CHALLENGE
    # ========================================================

    elif st.session_state.game == "reaction":
        st.subheader("⚡ Reaction Challenge")

        data = st.session_state.game_data

        if "target" not in data:
            data["target"] = random.choice(
                ["🟢", "🔵", "🟡", "🔴"]
            )
            data["start"] = time.time()

        if data.get("answered", False):
            st.success(
                f"⚡ Reaction time: "
                f"{data['final_time']:.2f} seconds"
            )

            st.metric(
                "Score",
                data["final_score"],
            )

            st.info(
                f"+{data['xp_reward']} XP earned!"
            )

            if st.button(
                "Back to Games",
                key="reaction_back",
            ):
                reset_game()
                st.rerun()

        else:
            target = data["target"]

            st.markdown(
                f"### Click the {target} button as quickly as possible!"
            )

            if st.button(
                target,
                key="reaction_button",
            ):
                elapsed = (
                    time.time()
                    - data["start"]
                )

                score = int(
                    max(
                        10,
                        150 - elapsed * 50,
                    )
                )
                score = min(100, score)

                data["answered"] = True

                finish_game(
                    child_id,
                    "Reaction Challenge",
                    "Reaction",
                    level,
                    score,
                    score,
                    elapsed,
                )

                st.rerun()


# ============================================================
# PROGRESS
# ============================================================

elif page == "📊 Progress":
    st.header("📊 My Brain Progress")

    df = get_game_scores(child_id)

    if df.empty:
        st.info(
            "Play some brain games to start building "
            "your progress history."
        )

    else:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "🧠 Memory",
            get_average_score(child_id, "Memory"),
        )

        col2.metric(
            "👀 Attention",
            get_average_score(child_id, "Attention"),
        )

        col3.metric(
            "🧩 Reasoning",
            get_average_score(child_id, "Reasoning"),
        )

        col4.metric(
            "⚡ Reaction",
            get_average_score(child_id, "Reaction"),
        )

        st.divider()

        category_df = (
            df.groupby("category")["score"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            category_df,
            x="category",
            y="score",
            title="Average Performance by Skill",
            range_y=[0, 100],
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.divider()

        df["played_at"] = pd.to_datetime(
            df["played_at"]
        )

        daily = (
            df.groupby(
                df["played_at"].dt.date
            )["score"]
            .mean()
            .reset_index()
        )

        daily.columns = [
            "Date",
            "Average Score",
        ]

        fig2 = px.line(
            daily,
            x="Date",
            y="Average Score",
            markers=True,
            title="Performance Over Time",
        )

        fig2.update_yaxes(
            range=[0, 100]
        )

        st.plotly_chart(
            fig2,
            use_container_width=True,
        )

        st.divider()

        st.subheader("🏆 Game History")

        history = df.copy()

        history["played_at"] = (
            history["played_at"]
            .dt.strftime("%Y-%m-%d %H:%M")
        )

        history = history[
            [
                "played_at",
                "game",
                "category",
                "level",
                "score",
                "accuracy",
                "time_taken",
            ]
        ]

        history.columns = [
            "Date",
            "Game",
            "Skill",
            "Level",
            "Score",
            "Accuracy",
            "Time",
        ]

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# PARENT VIEW
# ============================================================

elif page == "👨‍👩‍👧 Parent View":
    st.header("👨‍👩‍👧 Parent Dashboard")

    if not st.session_state.parent_authenticated:
        st.info(
            "Parent View is protected. Enter the parent PIN."
        )

        pin = st.text_input(
            "Parent PIN",
            type="password",
            key="parent_pin",
        )

        if st.button("Unlock Parent View", key="unlock_parent"):
            if pin == PARENT_PIN:
                st.session_state.parent_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN.")

        st.stop()

    st.success("Parent View unlocked.")

    if st.button("Lock Parent View", key="lock_parent"):
        st.session_state.parent_authenticated = False
        st.rerun()

    st.info(
        "This dashboard summarizes game performance. "
        "It should be treated as a progress indicator, "
        "not a medical or psychological diagnosis."
    )

    stats = get_child_stats(child_id)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Child", stats[0])
    col2.metric("Level", get_level(stats[2]))
    col3.metric("Stars", stats[1])
    col4.metric("XP", stats[2])

    st.divider()

    df = get_game_scores(child_id)

    if df.empty:
        st.info("No game performance data yet.")

    else:
        summary = (
            df.groupby("category")
            .agg(
                Average_Score=("score", "mean"),
                Games=("score", "count"),
                Best_Score=("score", "max"),
            )
            .reset_index()
        )

        summary["Average_Score"] = (
            summary["Average_Score"]
            .round(1)
        )

        st.subheader("🧠 Cognitive Skill Summary")

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader("📈 Recent Performance")

        df["played_at"] = pd.to_datetime(
            df["played_at"]
        )

        categories = df["category"].unique()

        for category in categories:
            category_data = (
                df[df["category"] == category]
                .sort_values("played_at")
            )

            if len(category_data) >= 2:
                first_score = category_data.iloc[0]["score"]
                latest_score = category_data.iloc[-1]["score"]
                difference = latest_score - first_score

                if difference > 0:
                    icon = "↗️"
                elif difference < 0:
                    icon = "↘️"
                else:
                    icon = "→"

                st.write(
                    f"**{category}:** "
                    f"{first_score:.0f} → "
                    f"{latest_score:.0f} "
                    f"{icon}"
                )
            else:
                st.write(
                    f"**{category}:** "
                    "Not enough data yet."
                )

        st.divider()

        st.subheader("🎮 Games Played")

        game_counts = (
            df["game"]
            .value_counts()
            .reset_index()
        )

        game_counts.columns = [
            "Game",
            "Times Played",
        ]

        st.dataframe(
            game_counts,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption("🧠 BrainQuest Kids")
st.sidebar.caption(
    "Short activities • Real-world routines • Progress tracking"
)
