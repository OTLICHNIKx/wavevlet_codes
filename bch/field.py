from dataclasses import dataclass, field as dataclass_field


DEFAULT_PRIMITIVE_POLYNOMIALS: dict[int, int] = {
    2: 0b111,        # x^2 + x + 1
    3: 0b1011,       # x^3 + x + 1
    4: 0b10011,      # x^4 + x + 1
    5: 0b100101,     # x^5 + x^2 + 1
    6: 0b1000011,    # x^6 + x + 1
    7: 0b10000011,   # x^7 + x + 1
    8: 0b100011101,  # x^8 + x^4 + x^3 + x^2 + 1
}


def integer_polynomial_degree(polynomial: int) -> int:
    """
    Возвращает степень полинома, записанного целым числом.

    Каждый бит является коэффициентом полинома.

    Например:

        0b1011 = x^3 + x + 1
    """
    if polynomial < 0:
        raise ValueError("Полином не может быть отрицательным")

    if polynomial == 0:
        return -1

    return polynomial.bit_length() - 1


@dataclass(frozen=True)
class GF2m:
    """
    Конечное поле GF(2^m).

    Элементы поля представлены целыми числами от 0 до 2^m - 1.

    Биты числа соответствуют коэффициентам полинома над GF(2).

    Например, в GF(2^3):

        0b101 = x^2 + 1

    primitive_polynomial должен иметь степень m.

    Например:

        x^3 + x + 1 -> 0b1011
    """

    m: int
    primitive_polynomial: int

    _exp_table: tuple[int, ...] = dataclass_field(
        init=False,
        repr=False,
    )

    _log_table: tuple[int, ...] = dataclass_field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.m <= 0:
            raise ValueError("m должно быть положительным")

        expected_degree = self.m
        actual_degree = integer_polynomial_degree(
            self.primitive_polynomial
        )

        if actual_degree != expected_degree:
            raise ValueError(
                "Степень примитивного полинома должна быть равна m: "
                f"m = {self.m}, степень = {actual_degree}"
            )

        if self.primitive_polynomial & 1 == 0:
            raise ValueError(
                "Свободный коэффициент примитивного полинома "
                "должен быть равен 1"
            )

        exp_table, log_table = self._build_logarithm_tables()

        object.__setattr__(
            self,
            "_exp_table",
            tuple(exp_table),
        )

        object.__setattr__(
            self,
            "_log_table",
            tuple(log_table),
        )

    @property
    def size(self) -> int:
        """
        Количество элементов поля:

            q = 2^m
        """
        return 1 << self.m

    @property
    def order(self) -> int:
        """
        Порядок мультипликативной группы ненулевых элементов:

            2^m - 1
        """
        return self.size - 1

    @property
    def element_mask(self) -> int:
        """
        Маска для хранения элемента поля в m битах.
        """
        return self.size - 1

    def validate_element(
        self,
        value: int,
        name: str = "value",
    ) -> int:
        """
        Проверяет, что значение является элементом поля.
        """
        if not isinstance(value, int):
            raise TypeError(f"{name} должен быть целым числом")

        if value < 0 or value >= self.size:
            raise ValueError(
                f"{name} должен находиться в диапазоне "
                f"от 0 до {self.size - 1}"
            )

        return value

    def add(self, left: int, right: int) -> int:
        """
        Сложение в GF(2^m).

        Сложение коэффициентов по модулю 2 эквивалентно XOR.
        """
        left = self.validate_element(left, name="left")
        right = self.validate_element(right, name="right")

        return left ^ right

    def subtract(self, left: int, right: int) -> int:
        """
        Вычитание совпадает со сложением, потому что:

            -a = a

        в поле характеристики 2.
        """
        return self.add(left, right)

    def multiply(self, left: int, right: int) -> int:
        """
        Умножение элементов поля через таблицы логарифмов.
        """
        left = self.validate_element(left, name="left")
        right = self.validate_element(right, name="right")

        if left == 0 or right == 0:
            return 0

        exponent = (
            self._log_table[left]
            + self._log_table[right]
        )

        return self._exp_table[exponent]

    def divide(self, numerator: int, denominator: int) -> int:
        """
        Деление элементов поля.
        """
        numerator = self.validate_element(
            numerator,
            name="numerator",
        )

        denominator = self.validate_element(
            denominator,
            name="denominator",
        )

        if denominator == 0:
            raise ZeroDivisionError(
                "Деление на нулевой элемент поля невозможно"
            )

        if numerator == 0:
            return 0

        exponent = (
            self._log_table[numerator]
            - self._log_table[denominator]
        ) % self.order

        return self._exp_table[exponent]

    def inverse(self, value: int) -> int:
        """
        Возвращает мультипликативно обратный элемент:

            value * inverse(value) = 1
        """
        value = self.validate_element(value)

        if value == 0:
            raise ZeroDivisionError(
                "Нулевой элемент не имеет обратного"
            )

        exponent = (
            self.order - self._log_table[value]
        ) % self.order

        return self._exp_table[exponent]

    def power(self, value: int, exponent: int) -> int:
        """
        Возводит элемент поля в целую степень.
        """
        value = self.validate_element(value)

        if not isinstance(exponent, int):
            raise TypeError("exponent должен быть целым числом")

        if exponent == 0:
            return 1

        if value == 0:
            if exponent < 0:
                raise ZeroDivisionError(
                    "Нельзя возвести ноль в отрицательную степень"
                )

            return 0

        logarithm = self._log_table[value]
        result_exponent = (logarithm * exponent) % self.order

        return self._exp_table[result_exponent]

    def alpha(self, exponent: int) -> int:
        """
        Возвращает степень примитивного элемента alpha.

            alpha^0 = 1
            alpha^1 = x
        """
        if not isinstance(exponent, int):
            raise TypeError("exponent должен быть целым числом")

        return self._exp_table[exponent % self.order]

    def logarithm(self, value: int) -> int:
        """
        Возвращает дискретный логарифм:

            value = alpha^logarithm(value)
        """
        value = self.validate_element(value)

        if value == 0:
            raise ValueError(
                "Дискретный логарифм нуля не определён"
            )

        return self._log_table[value]

    def _multiply_without_tables(
        self,
        left: int,
        right: int,
    ) -> int:
        """
        Полиномиальное умножение с редукцией.

        Используется при первоначальном построении таблиц поля.
        """
        result = 0
        a = left
        b = right

        while b:
            if b & 1:
                result ^= a

            b >>= 1
            a <<= 1

            if a & self.size:
                a ^= self.primitive_polynomial

        return result & self.element_mask

    def _build_logarithm_tables(
        self,
    ) -> tuple[list[int], list[int]]:
        """
        Строит таблицы степеней и логарифмов.

        Одновременно проверяет, что элемент x действительно является
        примитивным для заданного полинома.
        """
        base_exp_table: list[int] = []
        log_table = [-1] * self.size

        current = 1
        visited: set[int] = set()

        for exponent in range(self.order):
            if current == 0:
                raise ValueError(
                    "При построении поля получен нулевой элемент"
                )

            if current in visited:
                raise ValueError(
                    "Заданный полином не является примитивным: "
                    "степени элемента alpha повторились раньше времени"
                )

            visited.add(current)
            base_exp_table.append(current)
            log_table[current] = exponent

            current = self._multiply_without_tables(
                current,
                0b10,
            )

        if current != 1:
            raise ValueError(
                "После полного цикла примитивный элемент "
                "не вернулся к единице"
            )

        if len(visited) != self.order:
            raise ValueError(
                "Заданный полином не порождает все ненулевые "
                "элементы поля"
            )

        # Таблица дублируется, чтобы при умножении можно было
        # не вычислять остаток для суммы двух логарифмов.
        exp_table = base_exp_table + base_exp_table

        return exp_table, log_table


def create_gf2m(
    m: int,
    primitive_polynomial: int | None = None,
) -> GF2m:
    """
    Создаёт поле GF(2^m).

    Если primitive_polynomial не передан, используется полином
    из встроенной таблицы.
    """
    if primitive_polynomial is None:
        if m not in DEFAULT_PRIMITIVE_POLYNOMIALS:
            raise ValueError(
                "Для указанного m нет встроенного примитивного "
                "полинома. Передай primitive_polynomial явно."
            )

        primitive_polynomial = (
            DEFAULT_PRIMITIVE_POLYNOMIALS[m]
        )

    return GF2m(
        m=m,
        primitive_polynomial=primitive_polynomial,
    )