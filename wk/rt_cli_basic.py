from rhymetagger import RhymeTagger

poem = [
    [
	"Tell me not, in mournful numbers,",
	"Life is but an empty dream!",
	"For the soul is dead that slumbers,",
	"And things are not what they seem.",
	"Life is real! Life is earnest!",
	"And the grave is not its goal;",
	"Dust thou art, to dust returnest,",
	"Was not spoken of the soul.",

        "Tell me not, in mournful lumbers,",
        "Life is but an empty embers!",
        "For the soul is dead that dream,",
        "And things are not what they seem.",
        "Life is real! Life is invincible!",
        "And the grave is not its spectacle;",

	"Not enjoyment, and not sorrow,",
	"Is our destined end or way;",
	"But to act, that each tomorrow",
	"Find us farther than today.",
    # ],
    # [
    # "Tell me not, in mournful go,",
    # "Life is but an empty no!",
    # "For the soul is dead that bee,",
    # "And things are not what they sea.",
    # "Life is real! Life is mackerel!",
    # "And the grave is not its lobster;",
    # "Dust thou art, to dust mobster,",
    # "Was not spoken of the foo.",
    # "Not enjoyment, and not shampoo,",
    # "Is our destined end or melon;",
    # "But to act, that each felon",
    # "Find us farther than brink.",
    # ],
    # [
        "Tell me not, in mournful lumbers,",
        "Life is but an empty embers!",
        "For the soul is dead that glee,",
        "And things are not what they jamboree.",
        "Life is real! Life is invincible!",
        "And the grave is not its spectacle;",
    ]
]

poem_es = [
"La nostalgia del sol en los terrados,",
"en el muro color paloma de cemento",
"—sin embargo tan vivido— y el frío",
"repentino que casi sobrecoge.",
"La dulzura, el calor de los labios a solas",
"en medio de la calle familiar",
"igual que un gran salón, donde acudieran",
"multitudes lejanas como seres queridos.",
"Y sobre todo el vértigo del tiempo,",
"el gran boquete abriéndose hacia dentro del alma",
"mientras arriba sobrenadan promesas",
"que desmayan, lo mismo que si espumas.",
"Es sin duda el momento de pensar",
"que el hecho de estar vivo exige algo,",
"acaso heroicidades —o basta, simplemente,",
"alguna humilde cosa común",
"cuya corteza de materia terrestre",
"tratar entre los dedos, con un poco de fe?",
"Palabras, por ejemplo.",
"Palabras de familia gastadas tibiamente",
]

rt = RhymeTagger()
rt.load_model(model='en')

rtes = RhymeTagger()
rtes.load_model(model='es')

# rhymes = rt.tag(poem, output_format=3) 
# print(rhymes)

rhymes_es = rtes.tag(poem_es, output_format=3) 
print(rhymes_es)


