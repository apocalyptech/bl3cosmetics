#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import sys
import enum
from PIL import Image

class Collection:
    """
    A collection of screenshots which we'll display
    """

    def __init__(self, slug, name_plural, name_single, base_dir, contents=None):
        self.slug = slug
        self.name_plural = name_plural
        self.name_single = name_single
        self.base_dir = base_dir
        if contents:
            self.contents = contents
        else:
            self.contents = []

    def __len__(self):
        return len(self.contents)

    def get_filename(self):
        return os.path.join('_pages', f'{self.slug}.html')

class HostType(enum.Enum):
    """
    For shots with URLs attached to 'em, what's the source of the URL?  (We
    may be able to do fancy things like specify host-side resizes, for instance.)
    """
    NONE = enum.auto()
    GOOGLE = enum.auto()
    DROPBOX = enum.auto()
    OTHER = enum.auto()

class Shot:
    """
    A single screenshot, though possibly with some attached variants.
    """

    def __init__(self, name, filename, label=None, url=None, order=None, variants=None):
        self.name = name
        self.filename = filename
        self.base_dir = ''
        self.label = label
        self.order = order
        if variants:
            self.variants = variants
        else:
            self.variants = []

        # Process our URL (if we have one) -- some types are likely to have
        # bits we can strip out to find the "base" URL, just for ease of
        # copy+pasting
        if url:
            if 'googleusercontent.com' in url:
                if '=' in url:
                    self.url_base = url.split('=')[0]
                else:
                    self.url_base = url
                self.url_type = HostType.GOOGLE
            elif 'dropbox.com' in url:
                if '?' in url:
                    self.url_base = url.split('?')[0]
                else:
                    self.url_base = url
                self.url_type = HostType.DROPBOX
            else:
                self.url_base = url
                self.url_type = HostType.OTHER
        else:
            self.url_type = HostType.NONE
            self.url_base = None

    def __lt__(self, other):
        """
        Sorting -- Primary is the explicit `order` field.  Objects with this
        defined will go first.  `name` is our secondary, and if only one of us has
        it, the named object goes first.  Tertiary is `label`, and if only one of
        us has it, the one *without* the label goes first.  Finally we fall back
        to `filename`
        """
        if self.order is not None and other.order is not None:
            return self.order < other.order
        elif self.order is not None:
            return True
        elif other.order is not None:
            return False
        else:
            if self.name and other.name:
                return self.name.lower() < other.name.lower()
            elif self.name:
                return True
            elif other.name:
                return False
            else:
                if self.label and other.label:
                    return self.label.lower() < other.label.lower()
                elif self.label:
                    return False
                elif other.label:
                    return True
                else:
                    return self.filename.lower() < other.filename.lower()


class Variant(Shot):
    """
    Just a stupid wrapper for variant shots which don't have a "name" of their own.
    """

    def __init__(self, filename, label=None, url=None, order=None, variants=None):
        super().__init__(None, filename, label=label, url=url, order=order, variants=variants)

def main():

    collections = []
    collections.append(Collection('char-skins-beastmaster',
            'Beastmaster Skins',
            'Beastmaster Skin',
            'char_skins/beastmaster',
            [
                #Shot('Amp Stamp', 'amp_stamp.jpg'),
                #Shot('Anshin Wash Only', 'anshin_wash_only.jpg'),
                #Shot('Atlas Classic', 'atlas_classic.jpg'),
                Shot('Bad Astra', 'bad_astra.jpg'),
                Shot('Beastmaster Skin Default', 'beastmaster_skin_default.jpg', '(default skin)', order=1),
                Shot('Bubblegum Bum', 'bubblegum_bum.jpg'),
                #Shot('Burning Bright', 'burning_bright.jpg'),
                #Shot('Candy Raver', 'candy_raver.jpg'),
                #Shot('Caustic Bloom', 'caustic_bloom.jpg'),
                #Shot('Classic Look', 'classic_look.jpg'),
                #Shot('Clothed Circuit', 'clothed_circuit.jpg'),
                #Shot("Conventional Reppin'", 'conventional_reppin.jpg'),
                #Shot('Creature of the Night', 'creature_of_the_night.jpg'),
                #Shot('Crimson Raiment', 'crimson_raiment.jpg'),
                #Shot('Crook Look', 'crook_look.jpg'),
                #Shot('Dead Winter', 'dead_winter.jpg'),
                #Shot('Death by Filigrees', 'death_by_filigrees.jpg'),
                #Shot('Derringer Duds', 'derringer_duds.jpg'),
                #Shot('Devil Raider', 'devil_raider.jpg'),
                Shot('Ectoplasmic', 'ectoplasmic.jpg'),
                Shot('Electric Avenue', 'electric_avenue.jpg',
                    url='https://www.dropbox.com/s/pxnrb8bxpwd6ii7/electric_avenue.jpg?dl=0'),
                Shot('Extreme Caution', 'extreme_caution.jpg',
                    url='https://www.dropbox.com/s/unzkrei9sh81vl8/extreme_caution.jpg?dl=0'),
                Shot('Festive Vestments', 'festive_vestments.jpg',
                    url='https://www.dropbox.com/s/ay75sawy601033i/festive_vestments.jpg?dl=0'),
                Shot('Freedom Fashion', 'freedom_fashion.jpg',
                    url='https://www.dropbox.com/s/r0ywbxtxklr2wrq/freedom_fashion.jpg?dl=0'),
                Shot('Funk Off', 'funk_off.jpg'),
                #Shot('Gilded Rage', 'gilded_rage.jpg'),
                #Shot('Grand Archivist', 'grand_archivist.jpg'),
                #Shot('Grid Runner', 'grid_runner.jpg'),
                #Shot('Haunted Look', 'haunted_look.jpg'),
                #Shot('Hear Me Roar', 'hear_me_roar.jpg'),
                #Shot('Heart Attacker', 'heart_attacker.jpg'),
                #Shot('Heartbreaker', 'heartbreaker.jpg'),
                #Shot('Hex Bolts', 'hex_bolts.jpg'),
                #Shot('Horror Punk', 'horror_punk.jpg'),
                #Shot('Hot Rod', 'hot_rod.jpg'),
                #Shot('Hunting Season', 'hunting_season.jpg'),
                #Shot('Hyperion Beast', 'hyperion_beast.jpg'),
                #Shot('If Spooks Could Kill', 'if_spooks_could_kill.jpg'),
                #Shot('Jungle Jams', 'jungle_jams.jpg'),
                #Shot('Labradortilla', 'labradortilla.jpg'),
                #Shot('Le Chandail de Roland', 'le_chandail_de_roland.jpg'),
                #Shot('Like a Million Bucks', 'like_a_million_bucks.jpg'),
                #Shot('Like, Follow, Obey', 'like_follow_obey.jpg'),
                #Shot('Maliwan Mood', 'maliwan_mood.jpg'),
                #Shot('Moist the Flag', 'moist_the_flag.jpg'),
                #Shot('Muddy Slaughters', 'muddy_slaughters.jpg'),
                #Shot('Neon Dreams', 'neon_dreams.jpg'),
                #Shot('Oasis Chic', 'oasis_chic.jpg'),
                #Shot('Pimp My Raider', 'pimp_my_raider.jpg'),
                #Shot('Popsychle', 'popsychle.jpg'),
                #Shot('Ravenous', 'ravenous.jpg'),
                #Shot('Retro Futurist', 'retro_futurist.jpg'),
                #Shot('Runekeeper', 'runekeeper.jpg'),
                #Shot('Serene Siren', 'serene_siren.jpg'),
                #Shot('Ship It', 'ship_it.jpg'),
                #Shot('Signature Style', 'signature_style.jpg'),
                #Shot("Spec'd Out", 'specd_out.jpg'),
                #Shot('Spl4tter', 'spl4tter.jpg'),
                #Shot('Step One', 'step_one.jpg'),
                #Shot('Sure, Why Not?', 'sure_why_not.jpg'),
                #Shot('Teal Appeal', 'teal_appeal.jpg'),
                #Shot('Tentacular Spectacular', 'tentacular_spectacular.jpg'),
                #Shot('The Art of Stealth', 'the_art_of_stealth.jpg'),
                #Shot('THE H4RBINGER', 'the_h4rbinger.jpg'),
                #Shot('The Loader Look', 'the_loader_look.jpg'),
                #Shot('Trippy Hippie', 'trippy_hippie.jpg'),
                #Shot('Tropic Blunder', 'tropic_blunder.jpg'),
                #Shot('Urban Blammo', 'urban_blammo.jpg'),
                ]))

    for collection in collections:
        filename = collection.get_filename()
        print(f'Writing to {filename}...')
        with open(filename, 'w') as odf:
            print('---', file=odf)
            print(f'permalink: /{collection.slug}/', file=odf)
            print('---', file=odf)
            print('', file=odf)
            print(f'<h1>{collection.name_plural}</h1>', file=odf)
            print('', file=odf)
            if len(collection) == 1:
                report = collection.name_single
            else:
                report = collection.name_plural
            print('<strong>Total {}: {}</strong>'.format(
                report,
                len(collection),
                ), file=odf)

if __name__ == '__main__':
    main()

