# Type-Simulator
TypeSimulator is a Python tool designed to simulate human-like typing in text editors. It's useful for demonstrations, tutorials, and testing purposes. The tool uses `pyautogui` to control keyboard inputs, allowing it to type text into virtually any text editor or text input field.

## Features

- Simulate human-like typing with configurable speed and variance.
- Open a text editor or application before typing via a script.
- Type text provided directly via command line or from a text file.
- Handle special keys and sequences for more complex typing simulations.

## Usage

TypeSimulator can be run from the command line. There are several options available:

- `-e/--editor_script`: Path to a script to open the text editor or application.
- `-f/--file`: Path to a text file whose contents will be typed.
- `-s/--speed`: Typing speed in seconds per character. Default is 0.15 seconds.
- `-v/--variance`: Variance in typing speed to simulate natural typing. Default is 0.05 seconds.
- `text`: Direct text input to type.

### Example

To type the contents of a file with a custom typing speed:

`python typesimulator.py -f path/to/file.txt -s 0.1 -v 0.02`

To type a direct text input:

`python typesimulator.py "Hello, this is TypeSimulator!"`

## Customizing TypeSimulator

You can extend the functionality of TypeSimulator by editing the script. For example, you can add more special keys and sequences to the `_get_special_keys` method.

## License

This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT).

## Contributions

Contributions to this project are welcome. Please fork the repository and submit a pull request with your changes.
