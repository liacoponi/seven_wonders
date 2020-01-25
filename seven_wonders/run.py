from seven_wonders import definitions as sw
import csv
import random
import os


def main(no_of_players=4, card_file='cards.tsv', wonder_file='wonders.tsv'):
    wonders = load_wonders(wonder_file)
    players = [sw.Player(str(player)) for player in range(no_of_players)]
    decks = populate_decks(load_cards(card_file), no_of_players)
    play(players, decks, wonders)


def play(players, decks, wonders):
    print("** Wonders **")
    for i, p in enumerate(players):
        p.player_i = i
        random_wonder = random.randint(0, 7)
        p.wonder = iter(wonders[random_wonder + random.randint(0, 1)])
        del wonders[random_wonder:random_wonder+2]
        p.resources += p.wonder.resources
        print("Player {}: {}".format(p.name, p.wonder.name))
    for age, deck in enumerate(decks):
        print("\n** Beginning of age %s **" % str(age + 1))
        # create a deck for each player
        random.shuffle(deck)
        cards_per_deck = int(len(deck) / len(players))
        player_decks = [deck[cards_per_deck * i:cards_per_deck * (i + 1)] for i in range(0, len(players))]
        # Index used to track deck->player map. If it's 1, then p1 plays first, then p2 second, etc.
        deck_index = 0
        # until decks have one card left
        while len(player_decks[0]) > 1:
            # assign a deck to each player and play a card
            for p_i, player in enumerate(players):
                deck_i = (deck_index + p_i) % len(players)
                player.deck = player_decks[deck_i]
                player_decks[deck_i] = player.play_a_turn(players, player_decks[deck_i])
            # shift the decks to the right if it's age 2
            if age == 1:
                deck_index += 1
            else:
                deck_index -= 1
            print()

        print('** Fighting begins **')
        for p in range(len(players) - 1):
            players[p].military_tokens, players[p + 1].military_tokens = resolve_fight(players[p], players[p + 1], age)
            # First and last players also fight
        players[0].military_tokens, players[-1].military_tokens = resolve_fight(players[0], players[-1], age)
        print()

    for p in players:
        print("Player %s:\n\tResources: %s\n\tSplit resources: %s" % (p.name, p.resources, p.split_resources))

    calculate_victory_points(players)


def calculate_victory_points(players):
    def calc_guilds(p):
        return 0

    all_victory_points = dict()
    print("\n** Victory Points **")
    for p in players:
        victory_points = {
            'Military': p.military_tokens,
            'Treasury': p.resources['$'] // 3,
            'Wonder': p.resources['W'],
            'Blue cards': p.resources['V'],
            'Commerce': sum([card.resources['V'] for card in p.played_cards if getattr(card, 'color', None) == 'yellow']),
            'Science': p.resources['&'] ** 2 + p.resources['#'] ** 2 + p.resources['@'] +
                       7 * min([p.resources['&'], p.resources['#'], p.resources['@']]),
            'Guilds': calc_guilds(p)
        }
        victory_points['Total'] = sum(victory_points.values())
        formatted_points = ["\n{:>15}: {}".format(k, v) for k, v in victory_points.items()]
        print("\nPlayer %s:%s" % (p.name, ''.join(formatted_points)))
        all_victory_points[p.name] = victory_points['Total']

    print("\n**Ranking**",
          ''.join(["\n\tPlayer {}: {}".format(k, v) for k, v
                   in sorted(all_victory_points.items(), key=lambda item: item[1], reverse=True)]))


def resolve_fight(fighter_one, fighter_two, age):
    print("%s vs %s:" % (fighter_one.name, fighter_two.name), end=' ')
    if fighter_one.resources['X'] > fighter_two.resources['X']:
        # The formula gives 1, 3 and 5 victory points for age 1, 2, 3
        fighter_one.military_tokens += 1 + age * 2
        fighter_two.military_tokens -= 1
        print(fighter_one.name + " wins")
    elif fighter_one.resources['X'] < fighter_two.resources['X']:
        fighter_two.military_tokens += 1 + age * 2
        fighter_one.military_tokens -= 1
        print(fighter_two.name + " wins")
    else:
        print('draw!')
    return fighter_one.military_tokens, fighter_two.military_tokens


def load_cards(card_file='cards.tsv'):
    """Create a list of card object from a tsv file with card descriptions."""
    with open(os.path.join('data', card_file)) as card_file:
        card_reader = csv.reader(card_file, delimiter='\t')
        next(card_reader, None)
        return [sw.Card(line) for line in card_reader]


def populate_decks(card_list, no_of_players):
    """Returns a list of three shuffled decks"""
    decks = [[] for _ in range(3)]
    guild_cards = []
    for age in range(1, 4):
        for card in card_list:
            if card.age == age:
                if not card.cards_per_players:
                    # it's a guild card
                    guild_cards.append(card)
                    continue
                number_of_cards = card.cards_per_players[no_of_players - 1]
                for _ in range(0, number_of_cards):
                    decks[age - 1].append(card)
    # Add guild cards to age 3 deck
    random.shuffle(guild_cards)
    # According to Tofino
    decks[2] += guild_cards[0:no_of_players + 3]
    for deck in decks:
        random.shuffle(deck)
    return decks


def load_wonders(wonders_file):
    """Load list of wonders from a tsv file."""
    with open(os.path.join('data', wonders_file)) as w_file:
        wonder_reader = csv.reader(w_file, delimiter='\t')
        next(wonder_reader)
        wonders = {}
        for line in wonder_reader:
            if not line:
                continue
            try:
                name, cost, resources, stage, side = line
            except ValueError:
                raise ValueError('invalid line: ' + str(line))
            cost = sw.Resource(cost)
            name = name + '_' + side
            if resources.endswith('()'):
                resources = sw.Resource('V')
            elif '/' not in resources:
                resources = sw.Resource(resources)
            if name not in wonders:
                wonders[name] = sw.Wonder(name, side, resources)
            else:
                wonders[name].stages.append((cost, resources))
    return [wonders[wonder] for wonder in wonders.keys()]


if __name__ == '__main__':
    main(3)
