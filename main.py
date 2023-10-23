from account.question_and_answer.getAccountInfo import create_qa_chain
def main():
    chain = create_qa_chain()
    while True:
        command = input(">>> ")

        if command.lower() == "exit":
            print("Exiting...")
            break
        elif command.lower() == "help":
            print("Commands available:")
            print("help - Display this help menu")
            print("exit - Exit the prompt")
        else:
            chain.run(command)

if __name__ == "__main__":
    main()