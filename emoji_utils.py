# unicode digit emojis
# digits from '0' to '9'
zero_digit_code = zd = 48
# excluded digits
excl_digits = [2, 4, 5, 7]
# unicode digit keycap
udkc = '\U0000fe0f\U000020e3'
hours_0_9 = [chr(i) + udkc for i in range(zd, zd + 10)
         if i - zd not in excl_digits]
# number '10' emoji
hours_0_9.append('\U0001f51f')

# custom emojis from '11' to '23'
hours_11_23 = [str(i) for i in range(11, 24)]

vote = ('PLUS', 'MINUS')
edit = '\U0001F4DD'