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

```
python type_simulator.py -f path/to/file.txt -s 0.1 -v 0.02
```

![Peek 2024-03-02 20-55](https://github.com/djeada/Type-Simulator/assets/37275728/7d33a6a9-7502-4889-b19d-41aca85837a8)

To type a direct text input:

```
python type_simulator.py 'echo "Hello, this is TypeSimulator!" > temp.txt'
```

![Peek 2024-03-02 20-53](https://github.com/djeada/Type-Simulator/assets/37275728/e0f4ea67-e8d7-498a-82f3-439867457f6b)

## Customizing TypeSimulator

You can extend the functionality of TypeSimulator by editing the script. For example, you can add more special keys and sequences to the `_get_special_keys` method.

## License

This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT).

## Contributions

Contributions to this project are welcome. Please fork the repository and submit a pull request with your changes.
