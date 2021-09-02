#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import re
import sys
import json
import html
import enum
import lzma
import argparse
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
        """
        Allows us to use `len(collection_obj)`
        """
        return len(self.contents)

    def __iter__(self):
        """
        Allows us to iterate over the object
        """
        return iter(self.contents)

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
                    url = url.split('?')[0]
                self.url_base = f'{url}?raw=1'
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

    @property
    def anchor(self):
        return re.sub(r'[^a-zA-Z0-9]', '-', self.name.lower())

    def get_url(self, size):
        """
        Returns a URL with extra sizing parameters, if the URL type supports it.
        """
        if self.url_type == HostType.GOOGLE:
            return '{}=w{}-h{}-no?authuser=0'.format(
                    self.url_base,
                    size[0],
                    size[1],
                    )
        else:
            return self.url_base

class Variant(Shot):
    """
    Just a stupid wrapper for variant shots which don't have a "name" of their own.
    """

    def __init__(self, filename, label=None, url=None, order=None, variants=None):
        super().__init__(None, filename, label=label, url=url, order=order, variants=variants)


# Our collections!
bl3collections = []
bl3collections.append(Collection('char-skins-beastmaster',
        'Beastmaster Skins',
        'Beastmaster Skin',
        'char_skins/beastmaster',
        [
            Shot('Amp Stamp', 'amp_stamp.jpg',
                url='https://lh3.googleusercontent.com/QajO_JbAVvBE3yw_skIwjwbl2izuiOn6qTwp05Uc26lfALyQSGXr663KHjCLdpQsqSpBxsHRMnxk_wtA4hXo-M6tGqMyLRjVzTCHGqEvnq62J8P6Vxdba7dehMRi6dOh_59S5dBus6zqBhb_5BHTRFK77YVY-VK0ocnbnPjdw6Lf76MWIN0HN16j3cci99zOywTc5RvqpqCDcU8ky7ftFKiA2R1V-jA2odY5e6zc2R-9YZiJ1Jg42LUJHk2b8Wevwb-8ld7bL5JOR8qiMPYUtwl6jW0sAIIqRch8asDMuqX9dQfquelY_B2nuYp4kHjToQleyOfY1m-CqpDzTXBQm6SWY4KCGE0IJa58gKCO8K32Gj46EHjObk95jyfFJ8o1XsLO-upoxEBz43mXeb6vKW3pmkhYmxcllt_GVjUjDD6ztOntTH1wqDqzMrmErn7O85uFAu-uVB7aGeuv3LkhpD25k5mC6tSWqmw5d7uLEyYMzRBuvcPnUW3bLELEP-BEWEwy04QZHMqf33Vr15DeeBlpCzYk0Z_VrsAlTn_Iq02oRcgW0ILJTp0gnotSLIndJmt_utTkqF6jtXnKubS6sSoANSpGjmNOO5cch8b2HEbb2cvVmwS0zWgc8xUoqDu2J0Wi-q3uE9oz8zjjtf1QHcFoLMzBdEhXavWmxm2uJFwVkdQTqv05O-YHCY0oqH1cjVYYMt3ue-acWST2sUUW4JTP'),
            Shot('Anshin Wash Only', 'anshin_wash_only.jpg',
                url='https://lh3.googleusercontent.com/g11wPKBugLbIpoG3chc9BkFymuvV4aFeqIAcfosq0j5AyB9K427mCnJrbMAZoGal6UlOmRmu4ISl2st_rE7jEoqqUAnCAKfHpk5yyI9PppHEin5LVnu2MxnvXwWabO1u2C2vc5pXyoc0--BOknMEgYcwPxf9pSWIwYKzUvuUGk-lV0jpl6pC5_wCK8Z89ndOW6j5kQRijXAVMCS2pEFun_BdBNs29WKkfIb_9uAWNnqq6lsyIPZ0ukMLI_d7LSENanZwI6SmccBBvD3jTDShb0_e8R0C9nIemsv0fQnxLyUmKA6zQjSvprR6rbs1QRZAzZ7apTvtSlCklPG3fjpeF9s6ndRVKQ5rCJXUxYnXXMIx18VnwlyYqQGb8r33rJDiM-9NTgPw9TfiAM50f9ijhfUNiCHkQCPqspRohTjkliRXQjMUU8ijzOxPf7iNFrtlYF_kpwaN7a-gidy4HRFjeHXiFOoolkPpal9ul9s9yI9HmdhpDFRmI29YaRP6V9vkzlc4I4JVLItuvyI7hki-3PlLuydpNE0b_O7uB4MyhH87AudXzE4hDjyy7SL6aPP5k_C4ayPQ0cUNm_-Onot48B90-sj8F5yT-_eEVqloKu-Hhz7gp0ecPViBVug2Vs1HiqJltj-RARoRpgHwCocWjoCasEipBGQrZ3MZtzIaLQiSvYHVpe9lMK8JsIN-oAgK6Pom-t6C0YL1Qn80M7xKEFuD'),
            Shot('Atlas Classic', 'atlas_classic.jpg',
                url='https://lh3.googleusercontent.com/On6KmWCzr_3OVFkaQJbYY3nBbQ24zFh3MGql5CqgudGgWpKsQ3kjiiU_CL_u2eKjZljcjTedIwc3kSj8qILlFiG8S48Gw_2gkM0u_5d-HNBSoDrEjao_6NoGwtcW7s4aPAM3zIHjBuLdPRbv1f5WlvZHqgfLdrHsiSygd0XzEXeR-m57h4LzfNehS7mUvQwppEY4_UvZGJxhykPzutBnbU5usMXJApSgInCRlakzQD2yD0lkrYbbBau_IghmmFpMOCY6ioS1pksCv7USCn4w7F0xuycbyIk3kDESJ2esbXEj5x-v4DE24i7WOh8w8gSNKGlgICg7st4YN-vR2iJzNxiOhoTBETJg5kONVMmC0n426RILIYCrokHkTi78R0AxZGpFkbIfP3q0FeBN1lFeHgxzrnjH9YGOb3B_fUG-NqgrwQ_ZiJgwYIdmf28Qi7WQc_qhx2bbTH_UEAkq_jL71R-BdqdGEAAJGlCvwtLJvwBIA-KJaMUeo5dgYKnhk72TK8OO0XFQeORyvRYsoOYrOGgoiD3Q86oGxBgU1zqe6v-6Vp9BbyMJXKaLvkOT4NZ7x-B0Ey6HJI7UXmZWwU_9I3TcaAGUl1LsZUSBnxef-KY1u3iyJHciGWnj9uqG3uA-Ni2pxkA18DBWJ7G6kVZi7d5xbB5N9IH9rm7F4E5ti1GBGKNHHxPp3o0wYTVG6g-SWdcudaKhYFMnc1QzzIROPc88'),
            Shot('Bad Astra', 'bad_astra.jpg',
                url='https://lh3.googleusercontent.com/hb50kAVKvagE1l-RTHJKCeRqdjJERlxtuDT5PsD8Ij0PrBQYpXb_YzL1GzujILqwiWE6I7JDGzGeFRsIZI91xadV58oom01tiHLsJ8CqxzvSat7GLgJgyEpD0ZPhZ7DaZnNHMpJ-WUUe-LQ5WNiQ9hL7efHM95jH7f-8rDbdByLiE062hiLCEBsQJyk6WSI9ORlsW8mz01Wvrowt7rXwi85z3yaInfcJopql7C7R8mVeHd7DamIMJjDwzwO7xFJNrkAhYgc_UqJgLoUe0VAnvjecNsM5sDQG_aYr2yiB_sqEdWRsmiNX_onxPBlN1aBoYiU9_fNhLHlkICER1yOK5tz_ecU8FcdKtRKYpda84wScydxYsrLdNAddcF0bRwVrSe_kWkyMLj6eveJO7IqgLHyK8Eb7bpVRTJ5SzD2WqkxtaiUVpzYSlrVxvEdpqg3UZ4GkcUJ05mhPOOuQWPuhbyTkIcNfERkoRrDHht7luoLUusBWk_brywsxnLEYx4V0zBNevk_gCwWAOwwFvz_HCGuefr_ZOllMdAXiyTk7k6J1vUsMNGre4wF6LhgXYwpS7Ft-KpmYnMzd04wlHteCa9NPcm2br29k2qYRxpKzUYNUQdxMkpeMMJOOgVilY3Efndj2W5DnrSAnRe6pqsKpScyj1Ya-HOhL90cP5xYQH3b8xMhZelzvUd02Bj0GiiR8YGLflVIfhvT4aNFuY3Nqpflv'),
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

def main(thumb_size, urls=False, verbose=False):
    """
    Do the generation.

    if `urls` is `True`, use URLs instead of local files to do the linking.
    """

    global bl3collections

    # Cache of file mtimes, so we know whether or not to regenerate thumbnails
    cache_dir = '.cache'
    cache_file = os.path.join(cache_dir, 'shots.json.xz')
    cache_data = {}
    if os.path.exists(cache_file):
        with lzma.open(cache_file, 'r') as df:
            cache_data = json.load(df)

    # Loop through our collections and process 'em
    for collection in bl3collections:
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
            print('', file=odf)

            # Loop over shots
            for shot in sorted(collection):

                # Gather sizing info for the main image, and do resizes (or set up
                # serverside resizing URLs)
                if verbose:
                    print(' - Processing {}'.format(shot.name))
                image_filename = os.path.join('img', collection.base_dir, shot.filename)
                im = Image.open(image_filename)
                if urls and shot.url_type != HostType.NONE:
                    href_thumb = shot.get_url(thumb_size)
                    href_link = shot.get_url((im.width, im.height))
                else:
                    img_base, img_ext = shot.filename.rsplit('.', 1)
                    base_thumb = '{}-{}-{}.{}'.format(
                            img_base,
                            thumb_size[0],
                            thumb_size[1],
                            img_ext,
                            )
                    dir_thumb = os.path.join('thumbs', collection.base_dir)
                    full_thumb = os.path.join(dir_thumb, base_thumb)
                    if not os.path.exists(full_thumb):
                        if verbose:
                            print('   Generating thumbnail: {}'.format(full_thumb))
                        if not os.path.exists(dir_thumb):
                            os.makedirs(dir_thumb, exist_ok=True)
                        im.thumbnail(thumb_size)
                        im.save(full_thumb)
                    href_thumb = full_thumb
                    href_link = image_filename

                # Now output
                print('<div class="customization">', file=odf)
                print('<div class="title" id="{}">{}</div>'.format(
                    shot.anchor,
                    html.escape(shot.name),
                    ), file=odf)
                print('<a href="{}" class="image"><img src="{}" width="{}" alt="{}"></a>'.format(
                    href_link,
                    href_thumb,
                    thumb_size[0],
                    html.escape(shot.name, quote=True),
                    ), file=odf)
                if shot.label:
                    print('<div class="extra">{}</div>'.format(
                        html.escape(shot.label),
                        ), file=odf)
                print('</div>', file=odf)
                print('', file=odf)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
            description='Generate BL3 Cosmetics Archive',
            )

    parser.add_argument('-w', '--width',
            type=int,
            default=800,
            help='Width of inlined thumbnails',
            )

    parser.add_argument('-e', '--height',
            type=int,
            default=450,
            help='Height of inlined thumbnails',
            )

    parser.add_argument('-u', '--urls',
            action='store_true',
            help='Use URLs instead of local files, where possible.',
            )

    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='Output more status messages while processing',
            )

    args = parser.parse_args()

    main((args.width, args.height), args.urls, args.verbose)

