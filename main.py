from abc import ABC, abstractmethod
from collections import UserDict
from datetime import datetime, timedelta, date
import pickle


class Field:
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class Name(Field):
    pass


class Phone(Field):
    def __init__(self, value: str):
        if len(value) != 10 or not value.isdigit():
            raise ValueError("The phone number must contain 10 digits")
        super().__init__(value)


class Birthday(Field):
    def __init__(self, value: str):
        try:
            # Перетворення рядка на об'єкт datetime
            birthday = datetime.strptime(value, "%d.%m.%Y").date()

            # Перевірка, що дата не в майбутньому
            if birthday > date.today():
                raise ValueError(
                    "The date of birth cannot be greater than the current one."
                )

            self.value = birthday.strftime("%d.%m.%Y")

        except ValueError as e:
            raise ValueError(f"Invalid date: {e}. Use DD.MM.YYYY")


class Record:
    def __init__(self, name: str) -> None:
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone: str) -> None:
        self.phones.append(Phone(phone))

    def remove_phone(self, phone: str) -> None:
        for p in self.phones:
            if p.value == phone:
                self.phones.remove(p)

    def edit_phone(self, old_phone: str, new_phone: str) -> None:
        new_phone_obj = Phone(new_phone)
        for p in self.phones:
            if p.value == old_phone:
                p.value = new_phone_obj.value
                return
        raise ValueError(f"Phone {old_phone} not found")

    def add_birthday(self, birthday: str) -> None:
        self.birthday = Birthday(birthday)

    def __str__(self) -> str:
        phones = "; ".join(p.value for p in self.phones)
        birthday = f", birthday: {self.birthday.value}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones}{birthday}"


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Record:
        return self.data.get(name)

    def delete(self, name: str) -> None:
        if name in self.data:
            del self.data[name]

    @staticmethod
    def date_to_string(date: datetime):
        return date.strftime("%d.%m.%Y")

    @staticmethod
    def find_next_weekday(start_date: datetime, weekday: int) -> datetime:
        days_ahead = weekday - start_date.weekday()

        if days_ahead <= 0:
            days_ahead += 7

        return start_date + timedelta(days=days_ahead)

    @classmethod
    def adjust_for_weekend(cls, birthday: datetime) -> datetime:
        if birthday.weekday() >= 5:
            return cls.find_next_weekday(birthday, 0)
        return birthday

    def get_upcoming_birthdays(self, days: int = 7):
        upcoming_birthdays = []
        today = date.today()  # Зміна на date.today() для узгодження типу

        for record in self.data.values():
            if record.birthday:  # Перевірка наявності дня народження
                birthday_date = datetime.strptime(
                    record.birthday.value, "%d.%m.%Y"
                ).date()
                birthday_this_year = birthday_date.replace(year=today.year)

                # Оновлюємо рік, якщо день народження вже був цього року
                if birthday_this_year < today:
                    birthday_this_year = birthday_this_year.replace(year=today.year + 1)

                # Вираховуємо дні до дати привітання
                if 0 <= (birthday_this_year - today).days <= days:
                    birthday_this_year = self.adjust_for_weekend(birthday_this_year)
                    congratulation_date_str = self.date_to_string(birthday_this_year)
                    upcoming_birthdays.append(
                        {
                            "name": record.name.value,
                            "congratulation_date": congratulation_date_str,
                        }
                    )
        return upcoming_birthdays
    
    def save_data(book, filename="addressbook.pkl"):
        with open(filename, "wb") as file:
            pickle.dump(book, file)
        print("Address book saved to disk")

    def load_data(filename="addressbook.pkl"):
        try:
            with open(filename, "rb") as file:
                return pickle.load(file)
        except FileNotFoundError:
            return AddressBook()

    def __str__(self):
        if not self.data:
            return "AddressBook is empty"
        return "\n".join(str(record) for record in self.data.values())


# Базовий клас для уявлень
class View(ABC):
    @abstractmethod
    def display_message(self, message: str) -> None:
        pass
    
    @abstractmethod
    def input_command(self, prompt: str) -> str:
        pass

# Реалізація консольного інтерфейсу
class ConsoleView(View):
    def display_message(self, message: str) -> None:
        print(message)

    def input_command(self, prompt: str) -> str:
        return input(prompt)

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e)
            # return "Enter the argument for the command"
        except KeyError:
            return "Contact not found"
        except IndexError:
            return "Not enough argument for the command"

    return inner


def parse_input(user_input):
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def add_contact(args: list[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError("Please provide both a name and a phone number.")

    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."

    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."

    record.add_phone(phone)
    return message


@input_error
def change_contact(args: list[str], book: AddressBook) -> str:
    if len(args) < 3:
        raise ValueError("Please provide your name, old and new phone numbers.")

    name, old_phone, new_phone = args
    record = book.find(name)
    if not record:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Contact phone updated."


@input_error
def show_phone(args: list[str], book: AddressBook) -> str:
    name = args[0]
    record = book.find(name)
    if record:
        return f"{name}: {'; '.join(p.value for p in record.phones)}"
    return "Contact not found"


def show_all(book: AddressBook) -> str:
    return str(book)


@input_error
def add_birthday(args: list[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise ValueError("Please provide both a name and birthday date.")

    name, birthday = args
    record = book.find(name)
    if not record:
        raise KeyError
    record.add_birthday(birthday)
    return "Birthday added."


@input_error
def show_birthday(args: list[str], book: AddressBook) -> str:
    name = args[0]
    record = book.find(name)
    if record and record.birthday:
        return f"{name}'s birthday: {record.birthday.value}"
    return "Birthday not found"


@input_error
def birthdays(book: AddressBook) -> str:
    upcoming_birthdays = book.get_upcoming_birthdays()
    return "\n".join(
        f"{entry['name']}: {entry['congratulation_date']}"
        for entry in upcoming_birthdays
    )


def main() -> None:
    book = AddressBook.load_data()
    view = ConsoleView() # Використання конкретної реалізації уявлення
    view.display_message("Welcome to the assistant bot!")  # Показуємо повідомлення
 
    while True:
        user_input = view.input_command("Enter a command: ")
        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            book.save_data() 
            view.display_message("Good bye!")
            break
        elif command == "hello":
            view.display_message("How can I help you?")
        elif command == "add":
            view.display_message(add_contact(args, book))
        elif command == "change":
            view.display_message(change_contact(args, book))
        elif command == "phone":
            view.display_message(show_phone(args, book))
        elif command == "all":
            view.display_message(show_all(book))
        elif command == "add-birthday":
            view.display_message(add_birthday(args, book))
        elif command == "show-birthday":
            view.display_message(show_birthday(args, book))
        elif command == "birthdays":
            view.display_message(birthdays(book))
        else:
            view.display_message("Invalid command.")


if __name__ == "__main__":
    main()