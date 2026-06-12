from rantanplan.core import get_scansion

poem0 = """Me gustas cuando callas porque estás como ausente,
y me oyes desde lejos, y mi voz no te toca.
Parece que los ojos se te hubieran volado
y parece que un beso te cerrara la boca.

Como todas las cosas están llenas de mi alma
emerges de las cosas, llena del alma mía.
Mariposa de sueño, te pareces a mi alma,
y te pareces a la palabra melancolía."""

poem1 = """Sinto n’o peito us afogos
Que parece que m’o morden
Sete ducias de cans dogos.
Dis que son remordementos
D’os meus pecados á miles,
D’as miñas culpas á centos.
Culpas d’home mal cristiano
Pecados d’herexe, tales
Que non lles val zuruxano.
"""

poem2 = """La nostalgia del sol en los terrados,
en el muro color paloma de cemento
—sin embargo tan vivido— y el frío
repentino que casi sobrecoge."""


poem3 = """Esa inquietud que sin cesar te agita,
ese tormento que te oprime el pecho,
y pone abrojos al mullido lecho,
y tu semblante virginal marchita.
Esa lucha fatal que se concita
del corazón en el recinto estrecho,
y le arranca suspiros al despecho
en continua aflicción y amarga cuita;
ese dulce mirar, tu afecto tierno
que revelan un alma candorosa
que pugna por vencer un mal interno;
esa delicia, en fin, que misteriosa
con las penas se mezcla del infierno;
esa es la llama del amor, hermosa"""


poem4 = """Chile, fértil provincia y señalada
en la región antártica famosa,
de remotas naciones respetada
por fuerte, principal y poderosa;
la gente que produce es tan granada,
tan soberbia, gallarda y belicosa,
que no ha sido por rey jamás regida
ni a estranjero dominio sometida."""

poem5 = """Cualquier prisión y dolor
que se sufra es justa cosa,
pues se sufre por amor
de la mayor y mejor
del mundo y la más hermosa"""

poem6 = """Conde Niño por amores
es niño y bajó a la mar,
fue a dar agua a su caballo
la mañana de San Juan.
Desde las torres más altas
la reina le oyó cantar:
-Mira, niña, cómo canta
la sirenita del mar.
-No es la sirenita, madre,
que esa tiene otro cantar:
es la voz del conde Niño
que por mí llorando está.
-Guardias mandaba la reina
al conde Niño buscar,
que le maten a lanzadas
y su cuerpo echen al mar."""


poem7 = """
Conde Niño, por amores
es niño y pasó a la mar;
va a dar agua a su caballo
la mañana de San Juan.
Mientras el caballo bebe
él canta dulce cantar;
todas las aves del cielo
se paraban a escuchar;
caminante que camina
olvida su caminar,
navegante que navega
la nave vuelve hacia allá.
La reina estaba labrando,
la hija durmiendo está:
-Levantaos, Albaniña,
de vuestro dulce folgar,
sentiréis cantar hermoso
la sirenita del mar.
-No es la sirenita, madre,
la de tan bello cantar,
si no es el Conde Niño
que por mí quiere finar.
¡Quién le pudiese valer
en su tan triste penar!
-Si por tus amores pena,
¡oh, malhaya su cantar!,
y porque nunca los goce
yo le mandaré matar.
-Si le manda matar, madre
juntos nos han de enterrar.
Él murió a la media noche,
ella a los gallos cantar;
a ella como hija de reyes
la entierran en el altar,
a él como hijo de conde
unos pasos más atrás.
De ella nació un rosal blanco,
de él nació un espino albar;
crece el uno, crece el otro,
los dos se van a juntar;
las ramitas que se alcanzan
fuertes abrazos se dan,
y las que no se alcanzaban
no dejan de suspirar.
La reina, llena de envidia,
ambos los mandó cortar;
el galán que los cortaba
no cesaba de llorar;
della naciera una garza,
dél un fuerte gavilán
juntos vuelan por el cielo,
juntos vuelan a la par."""


poem8 = """Sinto n’o peito us afogos
Que parece que m’o morden
Sete ducias de cans dogos.
Dis que son remordementos
D’os meus pecados á miles,
D’as miñas culpas á centos.
Culpas d’home mal cristiano
Pecados d’herexe, tales
Que non lles val zuruxano.
Pra me curar bebin agoas,
Pisei herbas, recei tríos,
Biquei Santos, vertin bágoas.
Non hai festa ou romaría
Onde empanado non fose.
"""

poem10 = """El juego de hacer versos»
El juego de hacer versos
que no es un juego es algo
parecido en principio
al placer solitario.
Con la primera muda,
en los años nostálgicos
de nuestra adolescencia,
a escribir empezamos.
Y son nuestros poemas
del todo imaginarios
demasiado inexpertos"""


poem = poem10



myscan = get_scansion(poem, rhyme_analysis=True)

for verso in myscan:
    try:
        identificador_rima = verso["rhyme"]
        rima = verso["ending"]
        tipo_rima = verso["rhyme_type"]
        # para sacar la palabra rima
        verso_sin_puntuacion = [token for token in verso["tokens"]
                                if "word" in token]
        palabra_rima = "".join([silaba["syllable"] for silaba
                                in verso_sin_puntuacion[-1]["word"]])
        # mostrar los resultados
        print(f"{identificador_rima}\t{rima}\t{palabra_rima}\t{tipo_rima}")
    except Exception as e:
        print(f"Error: {e}")