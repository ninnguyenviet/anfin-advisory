.PHONY: run install clean run-admin run-requests

install:
	pip3 install -r requirements.txt

run:
	python3 -m streamlit run Leaderboard_Admin.py

run-requests:
	python3 -m streamlit run pages/2_Account_Requests.py
	
run-user-rank:
	python3 -m streamlit run pages/3_Advisory_User_Rank.py


clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
