import turtle
import math

turtle.init()

turtle.speed(0)
turtle.color('red')
turtle.bgcolor('black')

def corazon(n):
    x = 16 * math.sin(n) ** 3
    y = 13 * math.cos(n) - 5 * \
        math.cos(2*n) - math.cos(3*n) - \
        math.cos(4*n)
    return x, y

turtle.penup()
for i in range(15):
    turtle.goto(0,0)
    turtle.pendown()
    for n in range(0,100,2):
        x, y = corazon(n/10)
        turtle.goto(x*i, y*i)
    turtle.penup()

turtle.hideturtle()
turtle.done
