# Word App

A web application to help teach young children how to read and track their progress.

## Features

- Google OAuth authentication for user login
- Random word display for reading practice
- User feedback on correct/incorrect guesses
- Progress tracking for each user
- Data visualization of user performance

## Technologies Used

- Python
- FastHTML framework
- SQLite database
- Google OAuth for authentication
- HTMX for dynamic content updates

## Setup

1. Clone the repository
2. Install required dependencies (list them if available)
3. Set up Google OAuth credentials and update the client secret file path
4. Run the application using `python main.py`

## Usage

1. Log in using your Google account
2. Read the displayed word
3. Click 👍 if read correctly, 👎 if incorrect
4. Use the "Next" button to get a new word
5. View progress data on the /data route

## TODO

- Record the time that each guess was made
- Show the average time it took to guess each word
- Implement keyboard shortcuts for recording guesses and skipping to the next word
- Record the actual word that was guessed, not just its ID
- Show the user a preview of the next word before they click "Next"
- Display stats on guesses for each word when it's displayed
- Create an overall stats page
- Add or remove words to be shown
- Introduce difficulty levels for words
- Make the guessing game more fun with animations and sound effects
- Add ability to go back and forward between words
- Implement some sort of ordering of words
- Add ability to modify/control upcoming words
- Add custom words per user as well as starter words
- Implement time tracking for guesses
- Add keyboard shortcuts
- Create an overall stats page

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

[Add license information here]
