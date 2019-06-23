import random


def proto_test_case(data, fct):
    for input, expected_output in data:
        # print(input, expected_output, fct(input))
        actual_output = fct(input)
        if actual_output != expected_output:
            print('input: {} expected: {} got: {}'.format(input, expected_output, actual_output))
        assert actual_output == expected_output


def random_point():
    return random.uniform(-180, 180), random.uniform(-90, 90)


def list_of_random_points(length):
    return [random_point() for i in range(length)]
