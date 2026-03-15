#Шеснадцатиричные числа, у которых 3 справа цифры равна А16 расположенные в порядке убывания. Для каждой такой последовательности
# максимальное число вывести прописью.
file = open("text.txt",'r')
maxi = '0'
ch = ''
col = 0
col2 = 0
d = {0:'ноль',1:'один',2:'два',3:'три',4:'четыре',5:'пять',6:'шесть',7:'семь',8:'восемь',9:'девять',\
     10:'A',11:'B',12:'C',13:'D',14:'E',15:'F'}
buf = file.read(1)
if not buf:
        print("Файл пуст или не тот")
while buf:
    if buf != " ":
        ch = ch + buf
        buf = file.read(1)
    else:
        col+=1
        if len(ch) >=3 and ch[-3] == 'A':
            if int(ch,16) > int(maxi,16):
                col2 += 1
                maxi = ch
                for n in range(len(maxi)):
                    for l in range(len(d)):
                        if str(l) == maxi[n]:
                            print(d[l], end=' ')
                            break
                        elif d[l] == maxi[n]:
                            print(d[l], end=' ')
                print('')
            elif int(ch,16) < int(maxi,16):
                maxi = ch
        elif len(ch) < 3 or ch[-3] != 'A':
            maxi = '0'
        ch= ''
        buf = file.read(1)
if col2 == 0 and col > 0 :
     print("Нужных чисел не найдено")