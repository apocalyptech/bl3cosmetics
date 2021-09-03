#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import re
import sys
import json
import yaml
import html
import enum
import lzma
import argparse
from PIL import Image

class Category:
    """
    A category with multiple collections in it
    """

    def __init__(self, label, collections=None):
        self.label = label
        if collections:
            self.collections = collections
        else:
            self.collections = []

    def __len__(self):
        """
        Allows us to use `len(category_obj)`
        """
        return len(self.collections)

    def __iter__(self):
        """
        Allows us to iterate over the object
        """
        return iter(self.collections)

    def append(self, new_collection):
        self.collections.append(new_collection)

class Collection:
    """
    A collection of screenshots which we'll display
    """

    def __init__(self, slug, name_plural, name_single, base_dir, last_updated, contents=None, extra_text=None, grid=False):
        self.slug = slug
        self.name_plural = name_plural
        self.name_single = name_single
        self.base_dir = base_dir
        self.last_updated = last_updated
        self.extra_text = extra_text
        self.grid = grid
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
        self.parent = None
        if variants:
            self.variants = variants
            for variant in variants:
                variant.parent = self
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

    def output(self, odf, collection, base_img_href, thumb_size, urls=False, verbose=False):

        # Gather sizing info for the main image, and do resizes (or set up
        # serverside resizing URLs)
        if verbose:
            if self.name:
                print(' - Processing {}'.format(self.name))
            else:
                print('   Processing Variant')
        image_filename = os.path.join('img', collection.base_dir, self.filename)
        img_width = thumb_size[0]
        im = Image.open(image_filename)
        if urls and self.url_type != HostType.NONE:
            if im.width > thumb_size[0]:
                href_thumb = self.get_url(thumb_size)
            else:
                href_thumb = self.get_url((im.width, im.height))
                img_width = im.width
            href_link = self.get_url((im.width, im.height))
        else:
            if im.width > thumb_size[0]:
                img_base, img_ext = self.filename.rsplit('.', 1)
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
                href_thumb = f'{base_img_href}/{full_thumb}'
            else:
                href_thumb = f'{base_img_href}/{image_filename}'
                img_width = im.width
            href_link = f'{base_img_href}/{image_filename}'

        # Now output - first the header
        if collection.grid:
            print('<div class="grid-customization">', file=odf)
        else:
            print('<div class="customization">', file=odf)

        # Now the data
        if self.name:
            print('<div class="title" id="{}">{}</div>'.format(
                self.anchor,
                html.escape(self.name),
                ), file=odf)
        if self.name:
            alt_text = self.name
        elif self.parent:
            alt_text = self.parent.name
        if self.label:
            alt_text = '{} - {}'.format(alt_text, self.label)
        print('<a href="{}" class="image"><img src="{}" width="{}" alt="{}"></a>'.format(
            href_link,
            href_thumb,
            img_width,
            html.escape(alt_text, quote=True),
            ), file=odf)
        if self.label:
            print('<div class="extra">{}</div>'.format(
                html.escape(self.label),
                ), file=odf)

        # ... and footer.
        print('</div>', file=odf)
        print('', file=odf)

        # Display variants
        for variant in self.variants:
            variant.output(odf, collection, base_img_href, thumb_size, urls, verbose)

class Variant(Shot):
    """
    Just a stupid wrapper for variant shots which don't have a "name" of their own.
    """

    def __init__(self, filename, label=None, url=None, order=None, variants=None):
        super().__init__(None, filename, label=label, url=url, order=order, variants=variants)


# Our data!
char_heads = Category('Character Heads')
char_skins = Category('Character Skins')
other = Category('Other')
vehicles = Category('Vehicles')
categories = [char_heads, char_skins, other, vehicles]


###
### Our collections!  First up:
### Heads
###

char_heads.append(Collection('char-heads-beastmaster',
        'Beastmaster Heads',
        'Beastmaster Head',
        'char_heads/beastmaster',
        'Aug 6, 2021',
        [
            Shot("4ction Figure", '4ction_figure.jpg'),
            Shot("4NU Bust", '4nu_bust.jpg'),
            Shot("Abyss4l", 'abyss4l.jpg'),
            Shot("Anim4tronic", 'anim4tronic.jpg'),
            Shot("Antisoci4l", 'antisoci4l.jpg'),
            Shot("Bird Collar", 'bird_collar.jpg'),
            Shot("Bully for You", 'bully_for_you.jpg'),
            Shot("C4tch A Ride", 'c4tch_a_ride.jpg'),
            Shot("Camoufl4ge", 'camoufl4ge.jpg'),
            Shot("Cr4cked", 'cr4cked.jpg'),
            Shot("De4thless", 'de4thless.jpg'),
            Shot("Der4nged Ranger", 'der4nged_ranger.jpg'),
            Shot("Desperado", 'desperado.jpg'),
            Shot("Dre4dful Visage", 'dre4dful_visage.jpg'),
            Shot("FL4K", 'fl4k.jpg', '(default head)', order=1),
            Shot("FL4Kenstein's Monster", 'fl4kensteins_monster.jpg'),
            Shot("Grand Archivist", 'grand_archivist.jpg'),
            Shot("He4d in the Cloud", 'he4d_in_the_cloud.jpg'),
            Shot("Hotline Pandora", 'hotline_pandora.jpg'),
            Shot("Immort4l", 'immort4l.jpg'),
            Shot("Inh4ler", 'inh4ler.jpg'),
            Shot("Lance Helmet", 'lance_helmet.jpg'),
            Shot("Lumin4ry", 'lumin4ry.jpg'),
            Shot("Manta Ray", 'm4nta_ray.jpg'),
            Shot("Marcus Bobble", 'marcus_bobble.jpg'),
            Shot("Mendic4nt", 'mendic4nt.jpg'),
            Shot("Neon Predator", 'neon_predator.jpg'),
            Shot("NOG Mask", 'nog_mask.jpg'),
            Shot("Pony Up", 'pony_up.jpg'),
            Shot("Ratch Rider", 'ratch_rider.jpg'),
            Shot("Roll Player", 'roll_player.jpg'),
            Shot("Roy4lty", 'roy4lty.jpg'),
            Shot("Saurian Synth", 'saurian_synth.jpg'),
            Shot("Sh4man", 'sh4man.jpg'),
            Shot("Simul4crum", 'simul4crum.jpg'),
            Shot("Skagwave", 'skagwave.jpg'),
            Shot("Skull and Domes", 'skull_and_domes.jpg'),
            Shot("Skull Pl4te", 'skull_pl4te.jpg'),
            Shot("Spiderpunk", 'spiderpunk.jpg'),
            Shot("Str4nger", 'str4nger.jpg'),
            Shot("THE H4RBINGER", 'the_h4rbinger.jpg'),
            Shot("Tough Scruff", 'tough_scruff.jpg'),
            Shot("Tuned and Doomed", 'tuned_and_doomed.jpg'),
            Shot("Yok4i", 'yok4i.jpg'),
            ]))

char_heads.append(Collection('char-heads-gunner',
        'Gunner Heads',
        'Gunner Head',
        'char_heads/gunner',
        'Aug 6, 2021',
        [
            Shot("Antisocial", 'antisocial.jpg'),
            Shot("Bird Collar", 'bird_collar.jpg'),
            Shot("Black Eye", 'black_eye.jpg'),
            Shot("Bull Mozer", 'bull_mozer.jpg'),
            Shot("Bully for You", 'bully_for_you.jpg'),
            Shot("Commissar Andreyevna", 'commissar_andreyevna.jpg'),
            Shot("Conqueror", 'conqueror.jpg'),
            Shot("Cy-Ops", 'cy-ops.jpg'),
            Shot("Desperado", 'desperado.jpg'),
            Shot("Disengaged", 'disengaged.jpg'),
            Shot("Eyes on Target", 'eyes_on_target.jpg'),
            Shot("Fresh to Death", 'fresh_to_death.jpg'),
            Shot("Fuel Metal", 'fuel_metal.jpg'),
            Shot("Hotline Pandora", 'hotline_pandora.jpg'),
            Shot("Insulation", 'insulation.jpg'),
            Shot("Iron Baron", 'iron_baron.jpg'),
            Shot("Knight Watch", 'knight_watch.jpg'),
            Shot("Lance Helmet", 'lance_helmet.jpg'),
            Shot("Mad Moze", 'mad_moze.jpg'),
            Shot("Marcus Bobble", 'marcus_bobble.jpg'),
            Shot("Meowze", 'meowze.jpg'),
            Shot("Moze", 'moze.jpg', '(default head)', order=1),
            Shot("Mozo", 'mozo.jpg'),
            Shot("Neon Charger", 'neon_charger.jpg'),
            Shot("NOG Mask", 'nog_mask.jpg'),
            Shot("Outlaw", 'outlaw.jpg'),
            Shot("Pony Up", 'pony_up.jpg'),
            Shot("Ratch Rider", 'ratch_rider.jpg'),
            Shot("Roll Player", 'roll_player.jpg'),
            Shot("Saint of Iron", 'saint_of_iron.jpg'),
            Shot("Saurian Synth", 'saurian_synth.jpg'),
            Shot("Shark Tank", 'shark_tank.jpg'),
            Shot("Skagwave", 'skagwave.jpg'),
            Shot("Skull and Domes", 'skull_and_domes.jpg'),
            Shot("Spark of Genius", 'spark_of_genius.jpg'),
            Shot("Spiderpunk", 'spiderpunk.jpg'),
            Shot("Strange Angles", 'strange_angles.jpg'),
            Shot("Swooper Trooper", 'swooper_trooper.jpg'),
            Shot("The Garish Gunner", 'the_garish_gunner.jpg'),
            Shot("Tough Scruff", 'tough_scruff.jpg'),
            Shot("Toxic Behavior", 'toxic_behavior.jpg'),
            Shot("Tuned and Doomed", 'tuned_and_doomed.jpg'),
            Shot("Typhon's Legacy", 'typhons_legacy.jpg'),
            Shot("Weapons Haute", 'weapons_haute.jpg'),
            ]))

char_heads.append(Collection('char-heads-operative',
        'Operative Heads',
        'Operative Head',
        'char_heads/operative',
        'Aug 6, 2021',
        [
            Shot("Antihero", 'antihero.jpg'),
            Shot("Antisocial", 'antisocial.jpg'),
            Shot("Assassin One", 'assassin_one.jpg'),
            Shot("Bane Flynt", 'bane_flynt.jpg'),
            Shot("Bird Collar", 'bird_collar.jpg'),
            Shot("Bully for You", 'bully_for_you.jpg'),
            Shot("Chaotic Hood", 'chaotic_hood.jpg'),
            Shot("Crimson Operator", 'crimson_operator.jpg'),
            Shot("Crownin' Around", 'crownin_around.jpg'),
            Shot("Daredevil", 'daredevil.jpg'),
            Shot("Demon Could Weep", 'demon_could_weep.jpg'),
            Shot("Desperado", 'desperado.jpg'),
            Shot("Devilish Rogue", 'devilish_rogue.jpg'),
            Shot("Hard Bop", 'hard_bop.jpg'),
            Shot("Hombre", 'hombre.jpg'),
            Shot("Hotline Pandora", 'hotline_pandora.jpg'),
            Shot("Inzanity", 'inzanity.jpg'),
            Shot("Jawperative", 'jawperative.jpg'),
            Shot("Lance Helmet", 'lance_helmet.jpg'),
            Shot("Marcus Bobble", 'marcus_bobble.jpg'),
            Shot("Mythic", 'mythic.jpg'),
            Shot("Neon Mullet", 'neon_mullet.jpg'),
            Shot("NOG Mask", 'nog_mask.jpg'),
            Shot("One Last Job", 'one_last_job.jpg'),
            Shot("Oni", 'oni.jpg'),
            Shot("Pony Up", 'pony_up.jpg'),
            Shot("Ratch Rider", 'ratch_rider.jpg'),
            Shot("Regent", 'regent.jpg'),
            Shot("Roll Player", 'roll_player.jpg'),
            Shot("Ronin", 'ronin.jpg'),
            Shot("Saurian Synth", 'saurian_synth.jpg'),
            Shot("Shady Character", 'shady_character.jpg'),
            Shot("Skagwave", 'skagwave.jpg'),
            Shot("Skull and Domes", 'skull_and_domes.jpg'),
            Shot("Spiderpunk", 'spiderpunk.jpg'),
            Shot("Suction Filter", 'suction_filter.jpg'),
            Shot("Thinking Clearly", 'thinking_clearly.jpg'),
            Shot("Tough Scruff", 'tough_scruff.jpg'),
            Shot("Tuned and Doomed", 'tuned_and_doomed.jpg'),
            Shot("Tusk Raider", 'tusk_raider.jpg'),
            Shot("Wanderer", 'wanderer.jpg'),
            Shot("Weathered", 'weathered.jpg'),
            Shot("Wolfin' Shine", 'wolfin_shine.jpg'),
            Shot("Zane", 'zane.jpg', '(default head)', order=1),
            ]))

char_heads.append(Collection('char-heads-siren',
        'Siren Heads',
        'Siren Head',
        'char_heads/siren',
        'Aug 6, 2021',
        [
            Shot("A Few Scrapes", 'a_few_scrapes.jpg'),
            Shot("Amara", 'amara_default.jpg', '(default head)', order=1),
            Shot("Antisocial", 'antisocial.jpg'),
            Shot("Astral Empress", 'astral_empress.jpg'),
            Shot("Bird Collar", 'bird_collar.jpg'),
            Shot("Bonedana", 'bonedana.jpg'),
            Shot("Brick Top", 'brick_top.jpg'),
            Shot("Bully for You", 'bully_for_you.jpg'),
            Shot("Cat's Unforsaken Roar", 'cats_unforsaken_roar.jpg'),
            Shot("Chokella", 'chokella.jpg'),
            Shot("Con Martial Artist", 'con_martial_artist.jpg'),
            Shot("Cry Havoc", 'cry_havoc.jpg'),
            Shot("Cyber Hawk", 'cyber_hawk.jpg'),
            Shot("Desperado", 'desperado.jpg'),
            Shot("Full Coverage", 'full_coverage.jpg'),
            Shot("Hotline Pandora", 'hotline_pandora.jpg'),
            Shot("Jawbreaker", 'jawbreaker.jpg'),
            Shot("Killer Kitsune", 'killer_kitsune.jpg'),
            Shot("Lance Helmet", 'lance_helmet.jpg'),
            Shot("Mane Event", 'mane_event.jpg'),
            Shot("Marcus Bobble", 'marcus_bobble.jpg'),
            Shot("Mind Slayer", 'mind_slayer.jpg'),
            Shot("Motosaurus", 'motosaurus.jpg'),
            Shot("Neon Diva", 'neon_diva.jpg'),
            Shot("NOG Mask", 'nog_mask.jpg'),
            Shot("Partali Renegade", 'partali_renegade.jpg'),
            Shot("Pony Up", 'pony_up.jpg'),
            Shot("Psyren", 'psyren.jpg'),
            Shot("Pucker Up", 'pucker_up.jpg'),
            Shot("Ratch Rider", 'ratch_rider.jpg'),
            Shot("Roll Player", 'roll_player.jpg'),
            Shot("Saurian Synth", 'saurian_synth.jpg'),
            Shot("Sinister Sister", 'sinister_sister.jpg'),
            Shot("Siren's Cowl", 'sirens_cowl.jpg'),
            Shot("Skagwave", 'skagwave.jpg'),
            Shot("Skull and Domes", 'skull_and_domes.jpg'),
            Shot("Spiderpunk", 'spiderpunk.jpg'),
            Shot("Starry Eyed", 'starry_eyed.jpg'),
            Shot("Streamlined", 'streamlined.jpg'),
            Shot("Tiger of Spartali", 'tiger_of_spartali.jpg'),
            Shot("Tough Scruff", 'tough_scruff.jpg'),
            Shot("Transmission Vector", 'transmission_vector.jpg'),
            Shot("Tuned and Doomed", 'tuned_and_doomed.jpg'),
            Shot("Wired Science", 'wired_science.jpg'),
            ]))

###
### Skins
###

char_skins.append(Collection('char-skins-beastmaster',
        'Beastmaster Skins',
        'Beastmaster Skin',
        'char_skins/beastmaster',
        'Aug 6, 2021',
        [
            Shot('Amp Stamp', 'amp_stamp.jpg'),
            Shot('Anshin Wash Only', 'anshin_wash_only.jpg'),
            Shot('Atlas Classic', 'atlas_classic.jpg'),
            Shot('Bad Astra', 'bad_astra.jpg'),
            Shot('Beastmaster Skin Default', 'beastmaster_skin_default.jpg', '(default skin)', order=1),
            Shot('Bubblegum Bum', 'bubblegum_bum.jpg'),
            Shot('Burning Bright', 'burning_bright.jpg'),
            Shot('Candy Raver', 'candy_raver.jpg'),
            Shot('Caustic Bloom', 'caustic_bloom.jpg'),
            Shot('Classic Look', 'classic_look.jpg'),
            Shot('Clothed Circuit', 'clothed_circuit.jpg'),
            Shot("Conventional Reppin'", 'conventional_reppin.jpg'),
            Shot('Creature of the Night', 'creature_of_the_night.jpg'),
            Shot('Crimson Raiment', 'crimson_raiment.jpg'),
            Shot('Crook Look', 'crook_look.jpg'),
            Shot('Dead Winter', 'dead_winter.jpg'),
            Shot('Death by Filigrees', 'death_by_filigrees.jpg'),
            Shot('Derringer Duds', 'derringer_duds.jpg'),
            Shot('Devil Raider', 'devil_raider.jpg'),
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
            Shot('Gilded Rage', 'gilded_rage.jpg'),
            Shot('Grand Archivist', 'grand_archivist.jpg'),
            Shot('Grid Runner', 'grid_runner.jpg'),
            Shot('Haunted Look', 'haunted_look.jpg'),
            Shot('Hear Me Roar', 'hear_me_roar.jpg'),
            Shot('Heart Attacker', 'heart_attacker.jpg'),
            Shot('Heartbreaker', 'heartbreaker.jpg'),
            Shot('Hex Bolts', 'hex_bolts.jpg'),
            Shot('Horror Punk', 'horror_punk.jpg'),
            Shot('Hot Rod', 'hot_rod.jpg'),
            Shot('Hunting Season', 'hunting_season.jpg'),
            Shot('Hyperion Beast', 'hyperion_beast.jpg'),
            Shot('If Spooks Could Kill', 'if_spooks_could_kill.jpg'),
            Shot('Jungle Jams', 'jungle_jams.jpg'),
            Shot('Labradortilla', 'labradortilla.jpg'),
            Shot('Le Chandail de Roland', 'le_chandail_de_roland.jpg'),
            Shot('Like a Million Bucks', 'like_a_million_bucks.jpg'),
            Shot('Like, Follow, Obey', 'like_follow_obey.jpg'),
            Shot('Maliwan Mood', 'maliwan_mood.jpg'),
            Shot('Moist the Flag', 'moist_the_flag.jpg'),
            Shot('Muddy Slaughters', 'muddy_slaughters.jpg'),
            Shot('Neon Dreams', 'neon_dreams.jpg'),
            Shot('Oasis Chic', 'oasis_chic.jpg'),
            Shot('Pimp My Raider', 'pimp_my_raider.jpg'),
            Shot('Popsychle', 'popsychle.jpg'),
            Shot('Ravenous', 'ravenous.jpg'),
            Shot('Retro Futurist', 'retro_futurist.jpg'),
            Shot('Runekeeper', 'runekeeper.jpg'),
            Shot('Serene Siren', 'serene_siren.jpg'),
            Shot('Ship It', 'ship_it.jpg'),
            Shot('Signature Style', 'signature_style.jpg'),
            Shot("Spec'd Out", 'specd_out.jpg'),
            Shot('Spl4tter', 'spl4tter.jpg'),
            Shot('Step One', 'step_one.jpg'),
            Shot('Sure, Why Not?', 'sure_why_not.jpg'),
            Shot('Teal Appeal', 'teal_appeal.jpg'),
            Shot('Tentacular Spectacular', 'tentacular_spectacular.jpg'),
            Shot('The Art of Stealth', 'the_art_of_stealth.jpg'),
            Shot('THE H4RBINGER', 'the_h4rbinger.jpg'),
            Shot('The Loader Look', 'the_loader_look.jpg'),
            Shot('Trippy Hippie', 'trippy_hippie.jpg'),
            Shot('Tropic Blunder', 'tropic_blunder.jpg'),
            Shot('Urban Blammo', 'urban_blammo.jpg'),
            ]))

char_skins.append(Collection('char-skins-gunner',
        'Gunner Skins',
        'Gunner Skin',
        'char_skins/gunner',
        'Aug 6, 2021',
        [
            Shot('Amp Stamp', 'amp_stamp.jpg'),
            Shot('Anshin Wash', 'anshin_wash.jpg'),
            Shot('Atlas Classic', 'atlas_classic.jpg'),
            Shot('Bad Astra', 'bad_astra.jpg'),
            Shot('Bubblegum Bum', 'bubblegum_bum.jpg'),
            Shot('Burning Bright', 'burning_bright.jpg'),
            Shot('Candy Raver', 'candy_raver.jpg'),
            Shot('Caustic Bloom', 'caustic_bloom.jpg'),
            Shot('Classic Look', 'classic_look.jpg'),
            Shot('Clothed Circuit', 'clothed_circuit.jpg'),
            Shot('Commissar Andreyevna', 'commissar_andreyevna.jpg'),
            Shot("Conventional Reppin'", 'conventional_reppin.jpg'),
            Shot('Creature of the Night', 'creature_of_the_night.jpg'),
            Shot('Crimson Raiment', 'crimson_raiment.jpg'),
            Shot('Crook Look', 'crook_look.jpg'),
            Shot('Dead Winter', 'dead_winter.jpg'),
            Shot('Death by Filigrees', 'death_by_filigrees.jpg'),
            Shot('Derringer Duds', 'derringer_duds.jpg'),
            Shot('Devil Raider', 'devil_raider.jpg'),
            Shot('Ectoplasmic', 'ectoplasmic.jpg'),
            Shot('Electric Avenue', 'electric_avenue.jpg'),
            Shot('Extreme Caution', 'extreme_caution.jpg'),
            Shot('Festive Vestments', 'festive_vestments.jpg'),
            Shot('Freedom Fashion', 'freedom_fashion.jpg'),
            Shot('Funk Off', 'funk_off.jpg'),
            Shot('Gilded Rage', 'gilded_rage.jpg'),
            Shot('Grid Runner', 'grid_runner.jpg'),
            Shot('Gunner Skin Default', 'gunner_skin_default.jpg', '(default skin)', order=1),
            Shot('Haunted Look', 'haunted_look.jpg'),
            Shot('Hear Me Roar', 'hear_me_roar.jpg'),
            Shot('Heart Attacker', 'heart_attacker.jpg'),
            Shot('Heartbreaker', 'heartbreaker.jpg'),
            Shot('Hex Bolts', 'hex_bolts.jpg'),
            Shot('Horror Punk', 'horror_punk.jpg'),
            Shot('Hot Rod', 'hot_rod.jpg'),
            Shot('Hunting Season', 'hunting_season.jpg'),
            Shot('Hyperion Beast', 'hyperion_beast.jpg'),
            Shot('If Spooks Could Kill', 'if_spooks_could_kill.jpg'),
            Shot('Jungle Jams', 'jungle_jams.jpg'),
            Shot('Labradortilla', 'labradortilla.jpg'),
            Shot('Le Chandail de Roland', 'le_chandail_de_roland.jpg'),
            Shot('Like a Million Bucks', 'like_a_million_bucks.jpg'),
            Shot('Like, Follow, Obey', 'like_follow_obey.jpg'),
            Shot('Maliwan Mood', 'maliwan_mood.jpg'),
            Shot('Moist the Flag', 'moist_the_flag.jpg'),
            Shot('Muddy Slaughters', 'muddy_slaughters.jpg'),
            Shot('Neon Dreams', 'neon_dreams.jpg'),
            Shot('Oasis Chic', 'oasis_chic.jpg'),
            Shot('Pimp My Raider', 'pimp_my_raider.jpg'),
            Shot('Popsychle', 'popsychle.jpg'),
            Shot('Ravenous', 'ravenous.jpg'),
            Shot('Retro Futurist', 'retro_futurist.jpg'),
            Shot('Runekeeper', 'runekeeper.jpg'),
            Shot('Saint of Iron', 'saint_of_iron.jpg'),
            Shot('Serene Siren', 'serene_siren.jpg'),
            Shot('Ship It', 'ship_it.jpg'),
            Shot('Signature Style', 'signature_style.jpg'),
            Shot("Spec'd Out", 'specd_out.jpg'),
            Shot('Splatter', 'splatter.jpg'),
            Shot('Step One', 'step_one.jpg'),
            Shot('Sure, Why Not?', 'sure_why_not.jpg'),
            Shot('Teal Appeal', 'teal_appeal.jpg'),
            Shot('Tentacular Spectacular', 'tentacular_spectacular.jpg'),
            Shot('The Art of Stealth', 'the_art_of_stealth.jpg'),
            Shot('The Loader Look', 'the_loader_look.jpg'),
            Shot('Trippy Hippie', 'trippy_hippie.jpg'),
            Shot('Tropic Blunder', 'tropic_blunder.jpg'),
            Shot('Urban Blammo', 'urban_blammo.jpg'),
            ]))

char_skins.append(Collection('char-skins-operative',
        'Operative Skins',
        'Operative Skin',
        'char_skins/operative',
        'Aug 6, 2021',
        [
            Shot('Amp Stamp', 'amp_stamp.jpg'),
            Shot('Anshin Wash', 'anshin_wash.jpg'),
            Shot('Assassin One', 'assassin_one.jpg'),
            Shot('Atlas Classic', 'atlas_classic.jpg'),
            Shot('Bad Astra', 'bad_astra.jpg'),
            Shot('Bane Flynt', 'bane_flynt.jpg'),
            Shot('Bubblegum Bum', 'bubblegum_bum.jpg'),
            Shot('Burning Bright', 'burning_bright.jpg'),
            Shot('Candy Raver', 'candy_raver.jpg'),
            Shot('Caustic Bloom', 'caustic_bloom.jpg'),
            Shot('Classic Look', 'classic_look.jpg'),
            Shot('Clothed Circuit', 'clothed_circuit.jpg'),
            Shot("Conventional Reppin'", 'conventional_reppin.jpg'),
            Shot('Creature of the Night', 'creature_of_the_night.jpg'),
            Shot('Crimson Raiment', 'crimson_raiment.jpg'),
            Shot('Crook Look', 'crook_look.jpg'),
            Shot('Dead Winter', 'dead_winter.jpg'),
            Shot('Death by Filigrees', 'death_by_filigrees.jpg'),
            Shot('Derringer Duds', 'derringer_duds.jpg'),
            Shot('Devil Raider', 'devil_raider.jpg'),
            Shot('Ectoplasmic', 'ectoplasmic.jpg'),
            Shot('Electric Avenue', 'electric_avenue.jpg'),
            Shot('Extreme Caution', 'extreme_caution.jpg'),
            Shot('Festive Vestments', 'festive_vestments.jpg'),
            Shot('Freedom Fashion', 'freedom_fashion.jpg'),
            Shot('Funk Off', 'funk_off.jpg'),
            Shot('Gilded Rage', 'gilded_rage.jpg'),
            Shot('Grid Runner', 'grid_runner.jpg'),
            Shot('Haunted Look', 'haunted_look.jpg'),
            Shot('Hear Me Roar', 'hear_me_roar.jpg'),
            Shot('Heart Attacker', 'heart_attacker.jpg'),
            Shot('Heartbreaker', 'heartbreaker.jpg'),
            Shot('Hex Bolts', 'hex_bolts.jpg'),
            Shot('Horror Punk', 'horror_punk.jpg'),
            Shot('Hot Rod', 'hot_rod.jpg'),
            Shot('Hunting Season', 'hunting_season.jpg'),
            Shot('Hyperion Beast', 'hyperion_beast.jpg'),
            Shot('If Spooks Could Kill', 'if_spooks_could_kill.jpg'),
            Shot('Jungle Jams', 'jungle_jams.jpg'),
            Shot('Labradortilla', 'labradortilla.jpg'),
            Shot('Le Chandail de Roland', 'le_chandail_de_roland.jpg'),
            Shot('Like a Million Bucks', 'like_a_million_bucks.jpg'),
            Shot('Like, Follow, Obey', 'like_follow_obey.jpg'),
            Shot('Maliwan Mood', 'maliwan_mood.jpg'),
            Shot('Moist the Flag', 'moist_the_flag.jpg'),
            Shot('Muddy Slaughters', 'muddy_slaughters.jpg'),
            Shot('Neon Dreams', 'neon_dreams.jpg'),
            Shot('Oasis Chic', 'oasis_chic.jpg'),
            Shot('Operative Skin (default)', 'operative_skin_default.jpg', '(default skin)', order=1),
            Shot('Pimp My Raider', 'pimp_my_raider.jpg'),
            Shot('Popsychle', 'popsychle.jpg'),
            Shot('Ravenous', 'ravenous.jpg'),
            Shot('Retro Futurist', 'retro_futurist.jpg'),
            Shot('Runekeeper', 'runekeeper.jpg'),
            Shot('Serene Siren', 'serene_siren.jpg'),
            Shot('Ship It', 'ship_it.jpg'),
            Shot('Signature Style', 'signature_style.jpg'),
            Shot("Spec'd Out", 'specd_out.jpg'),
            Shot('Splatter', 'splatter.jpg'),
            Shot('Step One', 'step_one.jpg'),
            Shot('Sure, Why Not?', 'sure_why_not.jpg'),
            Shot('Teal Appeal', 'teal_appeal.jpg'),
            Shot('Tentacular Spectacular', 'tentacular_spectacular.jpg'),
            Shot('The Art of Stealth', 'the_art_of_stealth.jpg'),
            Shot('The Loader Look', 'the_loader_look.jpg'),
            Shot('Trippy Hippie', 'trippy_hippie.jpg'),
            Shot('Tropic Blunder', 'tropic_blunder.jpg'),
            Shot('Urban Blammo', 'urban_blammo.jpg'),
            ]))

char_skins.append(Collection('char-skins-siren',
        'Siren Skins',
        'Siren Skin',
        'char_skins/siren',
        'Aug 6, 2021',
        [
            Shot('Amp Stamp', 'amp_stamp.jpg'),
            Shot('Anshin Wash', 'anshin_wash.jpg'),
            Shot('Atlas Classic', 'atlas_classic.jpg'),
            Shot('Bad Astra', 'bad_astra.jpg'),
            Shot('Bubblegum Bum', 'bubblegum_bum.jpg'),
            Shot('Burning Bright', 'burning_bright.jpg'),
            Shot('Candy Raver', 'candy_raver.jpg'),
            Shot('Caustic Bloom', 'caustic_bloom.jpg'),
            Shot('Classic Look', 'classic_look.jpg'),
            Shot('Clothed Circuit', 'clothed_circuit.jpg'),
            Shot("Conventional Reppin'", 'conventional_reppin.jpg'),
            Shot('Creature of the Night', 'creature_of_the_night.jpg'),
            Shot('Crimson Raiment', 'crimson_raiment.jpg'),
            Shot('Crook Look', 'crook_look.jpg'),
            Shot('Dead Winter', 'dead_winter.jpg'),
            Shot('Death by Filigrees', 'death_by_filigrees.jpg'),
            Shot('Derringer Duds', 'derringer_duds.jpg'),
            Shot('Devil Raider', 'devil_raider.jpg'),
            Shot('Ectoplasmic', 'ectoplasmic.jpg'),
            Shot('Electric Avenue', 'electric_avenue.jpg'),
            Shot('Extreme Caution', 'extreme_caution.jpg'),
            Shot('Festive Vestments', 'festive_vestments.jpg'),
            Shot('Freedom Fashion', 'freedom_fashion.jpg'),
            Shot('Funk Off', 'funk_off.jpg'),
            Shot('Gilded Rage', 'gilded_rage.jpg'),
            Shot('Grid Runner', 'grid_runner.jpg'),
            Shot('Haunted Look', 'haunted_look.jpg'),
            Shot('Hear Me Roar', 'hear_me_roar.jpg'),
            Shot('Heart Attacker', 'heart_attacker.jpg'),
            Shot('Heartbreaker', 'heartbreaker.jpg'),
            Shot('Hex Bolts', 'hex_bolts.jpg'),
            Shot('Horror Punk', 'horror_punk.jpg'),
            Shot('Hot Rod', 'hot_rod.jpg'),
            Shot('Hunting Season', 'hunting_season.jpg'),
            Shot('Hyperion Beast', 'hyperion_beast.jpg'),
            Shot('If Spooks Could Kill', 'if_spooks_could_kill.jpg'),
            Shot('Jungle Jams', 'jungle_jams.jpg'),
            Shot('Labradortilla', 'labradortilla.jpg'),
            Shot('Le Chandail de Roland', 'le_chandail_de_roland.jpg'),
            Shot('Like a Million Bucks', 'like_a_million_bucks.jpg'),
            Shot('Like, Follow, Obey', 'like_follow_obey.jpg'),
            Shot('Maliwan Mood', 'maliwan_mood.jpg'),
            Shot('Moist the Flag', 'moist_the_flag.jpg'),
            Shot('Muddy Slaughters', 'muddy_slaughters.jpg'),
            Shot('Neon Dreams', 'neon_dreams.jpg'),
            Shot('Oasis Chic', 'oasis_chic.jpg'),
            Shot('Partali Renegade', 'partali_renegade.jpg'),
            Shot('Pimp My Raider', 'pimp_my_raider.jpg'),
            Shot('Popsychle', 'popsychle.jpg'),
            Shot('Ravenous', 'ravenous.jpg'),
            Shot('Retro Futurist', 'retro_futurist.jpg'),
            Shot('Runekeeper', 'runekeeper.jpg'),
            Shot('Serene Siren', 'serene_siren.jpg'),
            Shot('Ship It', 'ship_it.jpg'),
            Shot('Signature Style', 'signature_style.jpg'),
            Shot('Sinister Sister', 'sinister_sister.jpg'),
            Shot('Siren Skin Default', 'siren_skin_default.jpg', '(default skin)', order=1),
            Shot("Spec'd Out", 'specd_out.jpg'),
            Shot('Splatter', 'splatter.jpg'),
            Shot('Step One', 'step_one.jpg'),
            Shot('Sure, Why Not?', 'sure_why_not.jpg'),
            Shot('Teal Appeal', 'teal_appeal.jpg'),
            Shot('Tentacular Spectacular', 'tentacular_spectacular.jpg'),
            Shot('The Art of Stealth', 'the_art_of_stealth.jpg'),
            Shot('The Loader Look', 'the_loader_look.jpg'),
            Shot('Trippy Hippie', 'trippy_hippie.jpg'),
            Shot('Tropic Blunder', 'tropic_blunder.jpg'),
            Shot('Urban Blammo', 'urban_blammo.jpg'),
            ]))

###
### Other
###

other.append(Collection('echo-themes',
        'ECHO Themes',
        'ECHO Theme',
        'other/echo_themes',
        'Aug 6, 2021',
        [
            Shot("Accept the Charges", 'accept_the_charges.jpg', '(animated)'),
            Shot("Advanced Alien Technology", 'advanced_alien_technology.jpg', '(animated)'),
            Shot("Affection Connection", 'affection_connection.jpg', '(animated)'),
            Shot("AMD Red Chipper", 'amd_red_chipper.jpg'),
            Shot("Antique Chic", 'antique_chic.jpg'),
            Shot("AR-gyle Experience", 'ar-gyle_experience.jpg'),
            Shot("Birthday Dawg", 'birthday_dawg.jpg'),
            Shot("Call-A-Ride", 'call-a-ride.jpg'),
            Shot("Call A Ride", 'call_a_ride.jpg'),
            Shot("Candy Cane", 'candy_cane.jpg'),
            Shot("Chocolate Bubblegum", 'chocolate_bubblegum.jpg'),
            Shot("Classic Callback", 'classic_callback.jpg'),
            Shot("Clear Plastic (Cherry)", 'clear_plastic_cherry.jpg'),
            Shot("Clear Plastic (Dozer)", 'clear_plastic_dozer.jpg'),
            Shot("Clear Plastic (Ice)", 'clear_plastic_ice.jpg'),
            Shot("Clear Plastic (Jungle)", 'clear_plastic_jungle.jpg'),
            Shot("Clear Plastic (Steel)", 'clear_plastic_steel.jpg'),
            Shot("Comics Master", 'comics_master.jpg'),
            Shot("Convention Hero", 'convention_hero.jpg'),
            Shot("Cosmic Communicator", 'cosmic_communicator.jpg'),
            Shot("Cosmic Ring", 'cosmic_ring.jpg', '(animated)'),
            Shot("Crimson Blood Cell", 'crimson_blood_cell.jpg'),
            Shot("Crimson Graffiti", 'crimson_graffiti.jpg'),
            Shot("Dahl Kidz", 'dahl_kidz.jpg'),
            Shot("ECHO-3 Classic", 'echo-3_classic.jpg', '(default theme)', order=1),
            Shot("ECHOcardiogram", 'echocardiogram.jpg', '(animated)'),
            Shot("ECHO From Beyond", 'echo_from_beyond.jpg'),
            Shot("Electric Cell", 'electric_cell.jpg', '(animated)'),
            Shot("Electronics Master", 'electronics_master.jpg'),
            Shot("Executive Line", 'executive_line.jpg'),
            Shot("Eye Balls", 'eye_balls.jpg'),
            Shot("Eye Pad", 'eye_pad.jpg'),
            Shot("Field Trip", 'field_trip.jpg', '(animated)'),
            Shot("Final Destination", 'final_destination.jpg'),
            Shot("Fleshy", 'fleshy.jpg'),
            Shot("Game Comrade", 'game_comrade.jpg'),
            Shot("Glyphed Up the Receiver", 'glyphed_up_the_receiver.jpg'),
            Shot("Gold as the Grave", 'gold_as_the_grave.jpg'),
            Shot("Grapevine Hotline", 'grapevine_hotline.jpg', '(animated)'),
            Shot("Guac Shock", 'guac_shock.jpg'),
            Shot("Handheld Hunter", 'handheld_hunter.jpg'),
            Shot("HECKO-3", 'hecko-3.jpg'),
            Shot("Hot and Cold Call", 'hot_and_cold_call.jpg', '(animated)'),
            Shot("Hotwire Handheld", 'hotwire_handheld.jpg', '(animated)'),
            Shot("Industrial Chic", 'industrial_chic.jpg'),
            Shot("Loaded Sprinkles", 'loaded_sprinkles.jpg'),
            Shot("Local Service", 'local_service.jpg'),
            Shot("Maliwalkie-Talkie", 'maliwalkie-talkie.jpg'),
            Shot("Mecho-3", 'mecho-3.jpg', '(animated)'),
            Shot("Message from Beyond", 'message_from_beyond.jpg'),
            Shot("Occult Glow", 'occult_glow.jpg'),
            Shot("Paging Dr. Zed", 'paging_dr_zed.jpg'),
            Shot("Pepperoni Dream", 'pepperoni_dream.jpg'),
            Shot("Potato Phone", 'potato_phone.jpg'),
            Shot("Power Surge", 'power_surge.jpg'),
            Shot("Psychodelic", 'psychodelic.jpg'),
            Shot("Reinskag", 'reinskag.jpg', '(animated)'),
            Shot("Rockie Talkie", 'rockie_talkie.jpg'),
            Shot("Rocky Talkie", 'rocky_talkie.jpg'),
            Shot("Ruination", 'ruination.jpg'),
            Shot("Sand Line", 'sand_line.jpg'),
            Shot("Screen of Death", 'screen_of_death.jpg'),
            Shot("Snowglobe", 'snowglobe.jpg', '(animated)'),
            Shot("Space Catz", 'space_catz.jpg'),
            Shot("Stream DECH", 'stream_dech.jpg'),
            Shot("Tattoo Transmitter", 'tattoo_transmitter.jpg'),
            Shot("Tentacular", 'tentacular.jpg'),
            Shot("The Gortys Connection", 'the_gortys_connection.jpg'),
            Shot("Tina's Triple Trouble Terminal", 'tinas_triple_trouble_terminal.jpg', '(animated)'),
            Shot("Titan Up the Graphics", 'titan_up_the_graphics.jpg'),
            Shot("Tropical", 'tropical.jpg'),
            Shot("VECH-tor Graphics", 'vechtor_graphics.jpg'),
            Shot("VIP Status", 'vip_status.jpg'),
            ]))

other.append(Collection('room-decorations',
        'Room Decorations',
        'Room Decoration',
        'other/room_decorations',
        'Aug 6, 2021',
        [
            Shot("5KAGB8", '5kagb8.jpg'),
            Shot("5P8NKM3", '5p8nkm3.jpg'),
            Shot("Bandit Tire", 'bandit_tire.jpg'),
            Shot("Bellik Trophy", 'bellik_trophy.jpg'),
            Shot("Bloodwing Statue", 'bloodwing_statue.jpg'),
            Shot("Bug Zapper", 'bug_zapper.jpg'),
            Shot("Buzzsaw Blade", 'buzzsaw_blade.jpg'),
            Shot("Casino Banner", 'casino_banner.jpg'),
            Shot("Chemistry Set", 'chemistry_set.jpg', '(interactive)'),
            Shot("Core Lamp", 'core_lamp.jpg', '(interactive)'),
            Shot("COV Bat", 'cov_bat.jpg'),
            Shot("COV Buzzaxe", 'cov_buzzaxe.jpg'),
            Shot("COV Cleaver", 'cov_cleaver.jpg'),
            Shot("COV Engine Club", 'cov_engine_club.jpg'),
            Shot("COV Hammer", 'cov_hammer.jpg'),
            Shot("COV Sword", 'cov_sword.jpg'),
            Shot("COV Wrench", 'cov_wrench.jpg'),
            Shot("Dahl Bonded Blueprints", 'dahl_bonded_blueprints.jpg'),
            Shot("Dead Fish", 'dead_fish.jpg'),
            Shot("Decorative Bomb", 'decorative_bomb.jpg'),
            Shot("Dip Stick", 'dip_stick.jpg'),
            Shot("Dynasty Diner", 'dynasty_diner.jpg'),
            Shot("Framed Duchess", 'framed_duchess.jpg'),
            Shot("Framed Firewall", 'framed_firewall.jpg'),
            Shot("Framed Landscape", 'framed_landscape.jpg'),
            Shot("Framed Portal", 'framed_portal.jpg', '(interactive)'),
            Shot("Framed Tenderizer", 'framed_tenderizer.jpg'),
            Shot("Fyrestone", 'fyrestone.jpg'),
            Shot("Golden Buzz-Axe", 'golden_buzz-axe.jpg'),
            Shot("Hand Clock", 'hand_clock.jpg'),
            Shot("Handsome Jackpot", 'handsome_jackpot.jpg'),
            Shot("Hard Hat", 'hard_hat.jpg'),
            Shot("HBC Poster 1", 'hbc_poster_1.jpg'),
            Shot("HBC Poster 2", 'hbc_poster_2.jpg'),
            Shot("HBC Poster 3", 'hbc_poster_3.jpg'),
            Shot("HBC Poster 4", 'hbc_poster_4.jpg'),
            Shot("HBC Poster 5", 'hbc_poster_5.jpg'),
            Shot("HBC Poster 6", 'hbc_poster_6.jpg'),
            Shot("High Noon Clock", 'high_noon_clock.jpg'),
            Shot("Holo-Jack", 'holo-jack.jpg', '(interactive)'),
            Shot("Holy", 'holy.jpg'),
            Shot("Jack Mask", 'jack_mask.jpg'),
            Shot("Jack Plaque", 'jack_plaque.jpg'),
            Shot("Jakobs Poster", 'jakobs_poster.jpg'),
            Shot("Just Married Poster", 'just_married_poster.jpg'),
            Shot("Key to the City", 'key_to_the_city.jpg'),
            Shot("Killavolt's Shield", 'killavolts_shield.jpg'),
            Shot("Krieg's Mask", 'kriegs_mask.jpg'),
            Shot("Krieg's Moon", 'kriegs_moon.jpg'),
            Shot("Life Preserver", 'life_preserver.jpg'),
            Shot("Live Streaming", 'live_streaming.jpg'),
            Shot("Lunatic Shield", 'lunatic_shield.jpg'),
            Shot("Maya's Book", 'mayas_book.jpg'),
            Shot("Memory Orbs", 'memory_orbs.jpg'),
            Shot("Methane Monitor", 'methane_monitor.jpg'),
            Shot("Mounted Ratch", 'mounted_ratch.jpg'),
            Shot("Mounted Skag", 'mounted_skag.jpg'),
            Shot("Mounted Spiderant", 'mounted_spiderant.jpg'),
            Shot("Mouthpiece Mask", 'mouthpiece_mask.jpg'),
            Shot("Mouthpiece Speaker", 'mouthpiece_speaker.jpg'),
            Shot("Moxxi's Sign", 'moxxis_sign.jpg'),
            Shot("Neon Heart", 'neon_heart.jpg'),
            Shot("Neon Lips", 'neon_lips.jpg'),
            Shot("Neon Peach", 'neon_peach.jpg'),
            Shot("Old Guitar", 'old_guitar.jpg', '(interactive)'),
            Shot("Pandoracorn", 'pandoracorn.jpg'),
            Shot("Private Eye", 'private_eye.jpg'),
            Shot("Psycho Mask", 'psycho_mask.jpg'),
            Shot("Psychoreaver Trophy", 'psychoreaver_trophy.jpg'),
            Shot("R0ADK1L", 'r0adk1l.jpg'),
            Shot("Rampage of the Gorgonoth Poster", 'rampage_of_the_gorgonoth_poster.jpg'),
            Shot("Rocketeer Mask", 'rocketeer_mask.jpg'),
            Shot("Roland and Tina Photo", 'roland_and_tina_photo.jpg'),
            Shot("Ruiner Tapestry", 'ruiner_tapestry.jpg'),
            Shot("Safety First", 'safety_first.jpg'),
            Shot("Saloon Sign", 'saloon_sign.jpg'),
            Shot("Salvation", 'salvation.jpg'),
            Shot("Saxophone", 'saxophone.jpg'),
            Shot("Service Bot Console", 'service_bot_console.jpg'),
            Shot("Seven Smugglers Poster", 'seven_smugglers_poster.jpg'),
            Shot("Skag Attack", 'skag_attack.jpg'),
            Shot("Skag Skull", 'skag_skull.jpg'),
            Shot("Storm Brewin'", 'storm_brewin.jpg'),
            Shot("Talking Fish", 'talking_fish.jpg', '(interactive)'),
            Shot("The Big 3", 'the_big_3.jpg'),
            Shot("The Lodge Poster", 'the_lodge_poster.jpg'),
            Shot("The Martyr's Head", 'the_martyrs_head.jpg'),
            Shot("Three Fingers", 'three_fingers.jpg'),
            Shot("Trooper Disc", 'trooper_disc.jpg'),
            Shot("Trooper Shield", 'trooper_shield.jpg'),
            Shot("Trophy Fish", 'trophy_fish.jpg'),
            Shot("Troy Graffiti", 'troy_graffiti.jpg'),
            Shot("Tyreen Graffiti", 'tyreen_graffiti.jpg'),
            Shot("Use Protection", 'use_protection.jpg'),
            Shot("Vegan", 'vegan.jpg'),
            Shot("Warrior Horn", 'warrior_horn.jpg', '(interactive)'),
            Shot("Western Portrait 1", 'western_portrait_1.jpg'),
            Shot("Western Portrait 2", 'western_portrait_2.jpg'),
            Shot("Wotan's Head", 'wotans_head.jpg'),
            ]))

other.append(Collection('trinkets',
        'Trinkets',
        'Trinket',
        'other/trinkets',
        'Aug 6, 2021',
        grid=True,
        extra_text="Note: Only the trinket thumbnails are shown here",
        contents=[
            Shot("Action Axton", 'action_axton.png'),
            Shot("Adapt and Overcome", 'adapt_and_overcome.png'),
            Shot("AnarChic", 'anarchic.png'),
            Shot("Ascension", 'ascension.png'),
            Shot("A Shrinking Feeling", 'a_shrinking_feeling.png'),
            Shot("Battle Driver", 'battle_driver.png'),
            Shot("Beast Bowl", 'beast_bowl.png'),
            Shot("Book of the Storm", 'book_of_the_storm.png'),
            Shot("Born to Kill", 'born_to_kill.png'),
            Shot("Buckle Up", 'buckle_up.png'),
            Shot("Caster Blaster", 'caster_blaster.png'),
            Shot("Cloak and Swagger", 'cloak_and_swagger.png'),
            Shot("Cosmic Romance", 'cosmic_romance.png'),
            Shot("Dahl Tags", 'dahl_tags.png'),
            Shot("Deadeye Decal", 'deadeye_decal.png'),
            Shot("Dedication to Capitalism", 'dedication_to_capitalism.png'),
            Shot("De Leon's Lash", 'de_leons_lash.png'),
            Shot("Deploy and Destroy", 'deploy_and_destroy.png'),
            Shot("Devil Tooth", 'devil_tooth.png'),
            Shot("Diamond Ponytail", 'diamond_ponytail.png'),
            Shot("Divergent Thinking", 'divergent_thinking.png'),
            Shot("Drop It", 'drop_it.png'),
            Shot("Dry Heat", 'dry_heat.png'),
            Shot("Earn Your Stripes", 'earn_your_stripes.png'),
            Shot("Ellie's Power Flower", 'ellies_power_flower.png'),
            Shot("Explosives Enthusiast", 'explosives_enthusiast.png'),
            Shot("For Funsies", 'for_funsies.png'),
            Shot("Frakkin' Toaster", 'frakkin_toaster.png'),
            Shot("Gearbox Fan", 'gearbox_fan.png'),
            Shot("God-King's Bling", 'god-kings_bling.png'),
            Shot("Gold Tier", 'gold_tier.png'),
            Shot("Goodnight Kiss", 'goodnight_kiss.png'),
            Shot("Guardian's Lament", 'guardians_lament.png'),
            Shot("Hat Trick", 'hat_trick.png'),
            Shot("H Marks the Spot", 'h_marks_the_spot.png'),
            Shot("Hoops Dreams", 'hoops_dreams.png'),
            Shot("Hunter's Patch", 'hunters_patch.png'),
            Shot("Itsy Bitsy Rakky Hive", 'itsy_bitsy_rakky_hive.png'),
            Shot("Jack's Off", 'jacks_off.png'),
            Shot("Just In Case", 'just_in_case.png'),
            Shot("Kaboom Bunny", 'kaboom_bunny.png'),
            Shot("Keep Your Eye Out", 'keep_your_eye_out.png'),
            Shot("King's Knight", 'kings_knight.png'),
            Shot("Last Ride", 'last_ride.png'),
            Shot("Li'l Chomper", 'lil_chomper.png'),
            Shot("Mercenary Day Ornament", 'mercenary_day_ornament.png'),
            Shot("Neon Skelly", 'neon_skelly.png'),
            Shot("Nibblenomicon", 'nibblenomicon.png'),
            Shot("Nothing Gold Can Stay", 'nothing_gold_can_stay.png'),
            Shot("No, You're Crazy", 'no_youre_crazy.png'),
            Shot("Null and V0id", 'null_and_v0id.png'),
            Shot("One Army", 'one_army.png'),
            Shot("One Shot", 'one_shot.png'),
            Shot("On the Hunt", 'on_the_hunt.png'),
            Shot("Pain Freeze", 'pain_freeze.png', "Currently bugged - inventory icon doesn't work"),
            Shot("Pandora Sunset", 'pandora_sunset.png'),
            Shot("Queen of Hearts", 'queen_of_hearts.png'),
            Shot("Relaxtrap", 'relaxtrap.png'),
            Shot("Retro Outrunner", 'retro_outrunner.png'),
            Shot("Rhys's Piece", 'rhys_piece.png'),
            Shot("Shooter's Shuttle", 'shooters_shuttle.png'),
            Shot("Shrunk 'n Dead", 'shrunk_n_dead.png'),
            Shot("Sign of the Hawk", 'sign_of_the_hawk.png'),
            Shot("Siren's Mark", 'sirens_mark.png'),
            Shot("Slot Shot", 'slot_shot.png'),
            Shot("Splorghuld, the Flesh-Slayer", 'splorghuld.png'),
            Shot("Stink Eye", 'stink_eye.png'),
            Shot("Super General Claptrap", 'super_general_claptrap.png'),
            Shot("Switch Hitter", 'switch_hitter.png'),
            Shot("Tactical Tentacle", 'tactical_tentacle.png'),
            Shot("Tchotchkey", 'tchotchkey.png'),
            Shot("Tentacle Ventricles", 'tentacle_ventricles.png'),
            Shot("Tinker's Trinket", 'tinkers_trinket.png'),
            Shot("Tiny Vault", 'tiny_vault.png'),
            Shot("Track and Destroy", 'track_and_destroy.png'),
            Shot("Turtle Up", 'turtle_up.png'),
            Shot("Vapor Hoodlum", 'vapor_hoodlum.png'),
            Shot("Vault Insider VIP", 'vault_insider_vip.png'),
            Shot("Warm Welcome", 'warm_welcome.png'),
            Shot("When In Doubt, Chuck It", 'when_in_doubt.png'),
            Shot("Who Needs Gods?", 'who_needs_gods.png'),
            Shot("Wittle Warrior", 'wittle_warrior.png'),
            ]))

other.append(Collection('weapon-skins',
        'Weapon Skins',
        'Weapon Skin',
        'other/weapon_skins',
        'Aug 6, 2021',
        extra_text="Skins shown on a Crader's EM-P5",
        contents=[
            Shot("Black Dragon", 'black_dragon.jpg'),
            Shot("Blueberry Limeade", 'blueberry_limeade.jpg'),
            Shot("Burnished Steele", 'burnished_steele.jpg'),
            Shot("Butt Dazzle", 'butt_dazzle.jpg', '(animated)'),
            Shot("Crepuscule", 'crepuscule.jpg'),
            Shot("Dandy Lion", 'dandy_lion.jpg'),
            Shot("Dead Set", 'dead_set.jpg'),
            Shot("Deep Nebula", 'deep_nebula.jpg', '(animated)'),
            Shot("Digital Horizons", 'digital_horizons.jpg'),
            Shot("DLC3 WeaponSkin", 'dlc_weaponskin.jpg',
                'Unfinished (visually identical to Burnished Steele), and unobtainable ' +
                'without shenanigans, but nonetheless "technically" exists in the game.'),
            Shot("Extraspectral", 'extraspectral.jpg'),
            Shot("Fire and Ash", 'fire_and_ash.jpg'),
            Shot("Gearbox Prime", 'gearbox_prime.jpg'),
            Shot("Ghoul Metal Grey", 'ghoul_metal_grey.jpg', '(animated)'),
            Shot("Goldie Locks and Loads", 'goldie_locks_and_loads.jpg'),
            Shot("Gun-fetti", 'gun-fetti.jpg'),
            Shot("Homecoming", 'homecoming.jpg'),
            Shot("Hot Blooded", 'hot_blooded.jpg'),
            Shot("Ink and Kill", 'ink_and_kill.jpg'),
            Shot("It's Poop!", 'its_poop.jpg'),
            Shot("Leather and Regret", 'leather_and_regret.jpg'),
            Shot("Maliwannabe", 'maliwannabe.jpg'),
            Shot("Painbow", 'painbow.jpg'),
            Shot("Phaselocked and Loaded", 'phaselocked_and_loaded.jpg'),
            Shot("Porphyrophobia", 'porphyrophobia.jpg'),
            Shot("Psychodelic", 'psychodelic.jpg', '(animated)'),
            Shot("Red Sands", 'red_sands.jpg'),
            Shot("Retro Blaster", 'retro_blaster.jpg'),
            Shot("Runic Relic", 'runic_relic.jpg'),
            Shot("Scoot and Loot", 'scoot_and_loot.jpg'),
            Shot("Skelebones", 'skelebones.jpg'),
            Shot("Super Oaker", 'super_oaker.jpg'),
            Shot("Thunderhead", 'thunderhead.jpg', '(animated)'),
            ]))

###
### Vehicles
###

vehicles.append(Collection('outrunner',
        'Outrunner Skins',
        'Outrunner Skin',
        'vehicle_skins/outrunner',
        'Mar 26, 2020',
        [
            Shot("Angel", 'angel_1_regular.jpg', 'light armor', variants=[
                Variant('angel_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Atlas", 'atlas_1_regular.jpg', 'light armor', variants=[
                Variant('atlas_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Bubblegum", 'bubblegum_1_regular.jpg', 'light armor', variants=[
                Variant('bubblegum_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Bug Racer", 'bug_racer_1_regular.jpg', 'light armor', variants=[
                Variant('bug_racer_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Children of the Vault", 'children_of_the_vault_1_regular.jpg', 'light armor', variants=[
                Variant('children_of_the_vault_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Dahl", 'dahl_1_regular.jpg', 'light armor', variants=[
                Variant('dahl_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Default", 'default_1_regular.jpg', 'light armor (default skin)', order=1, variants=[
                Variant('default_2_heavy.jpg', 'heavy armor (default skin)'),
                ]),
            Shot("Ellie", 'ellie_1_regular.jpg', 'light armor', variants=[
                Variant('ellie_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Festive", 'festive_1_regular.jpg', 'light armor', variants=[
                Variant('festive_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Flames", 'flames_1_regular.jpg', 'light armor', variants=[
                Variant('flames_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Forest", 'forest_1_regular.jpg', 'light armor', variants=[
                Variant('forest_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Gearbox", 'gearbox_1_regular.jpg', 'light armor', variants=[
                Variant('gearbox_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Golden Hog", 'golden_hog_1_regular.jpg', 'light armor', variants=[
                Variant('golden_hog_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Grog Lube", 'grog_lube_1_regular.jpg', 'light armor', variants=[
                Variant('grog_lube_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Hexagons", 'hexagons_1_regular.jpg', 'light armor', variants=[
                Variant('hexagons_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Historic Racing", 'historic_racing_1_regular.jpg', 'light armor', variants=[
                Variant('historic_racing_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Houndstooth", 'houndstooth_1_regular.jpg', 'light armor', variants=[
                Variant('houndstooth_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Hyperion", 'hyperion_1_regular.jpg', 'light armor', variants=[
                Variant('hyperion_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Infection", 'infection_1_regular.jpg', 'light armor', variants=[
                Variant('infection_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Jakobs", 'jakobs_1_regular.jpg', 'light armor', variants=[
                Variant('jakobs_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Maliwan", 'maliwan_1_regular.jpg', 'light armor', variants=[
                Variant('maliwan_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Pirate", 'pirate_1_regular.jpg', 'light armor', variants=[
                Variant('pirate_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Prisa's Garage", 'prisas_garage_1_regular.jpg', 'light armor', variants=[
                Variant('prisas_garage_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Psycho-mobile", 'psycho-mobile_1_regular.jpg', 'light armor', variants=[
                Variant('psycho-mobile_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Rage Cage", 'rage_cage_1_regular.jpg', 'light armor', variants=[
                Variant('rage_cage_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Red Machine", 'red_machine_1_regular.jpg', 'light armor - BUGGED, can only spawn at exactly level 9', variants=[
                Variant('red_machine_2_heavy.jpg', 'heavy armor - BUGGED, can only spawn at exactly level 9'),
                ]),
            Shot("Shirking Convention", 'shirking_convention_1_regular.jpg', 'light armor', variants=[
                Variant('shirking_convention_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Slow and Mad", 'slow_and_mad_1_regular.jpg', 'light armor', variants=[
                Variant('slow_and_mad_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Spicy Tuna Roll", 'spicy_tuna_roll_1_regular.jpg', 'light armor', variants=[
                Variant('spicy_tuna_roll_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Stealth", 'stealth_1_regular.jpg', 'light armor', variants=[
                Variant('stealth_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Tentacar", 'tentacar_1_regular.jpg', 'light armor', variants=[
                Variant('tentacar_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Torgue", 'torgue_1_regular.jpg', 'light armor', variants=[
                Variant('torgue_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Triangles", 'triangles_1_regular.jpg', 'light armor', variants=[
                Variant('triangles_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Vladof", 'vladof_1_regular.jpg', 'light armor', variants=[
                Variant('vladof_2_heavy.jpg', 'heavy armor'),
                ]),
            ]))

vehicles.append(Collection('cyclone',
        'Cyclone Skins',
        'Cyclone Skin',
        'vehicle_skins/cyclone',
        'Mar 26, 2020',
        [

            Shot("Atlas", 'atlas_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('atlas_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Bubblegum", 'bubblegum_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('bubblegum_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Children of the Vault", 'children_of_the_vault_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('children_of_the_vault_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Chopper", 'chopper_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('chopper_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Dahl", 'dahl_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('dahl_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Dark", 'dark_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('dark_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Default", 'default_1_heavy_blade.jpg', 'heavy armor, blade wheel (default skin)', order=1, variants=[
                Variant('default_2_regular_hover.jpg', 'light armor, hover wheel (default skin)'),
                ]),
            Shot("Ellie", 'ellie_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('ellie_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Emergency", 'emergency_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('emergency_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Firehawk", 'firehawk_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('firehawk_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Forest", 'forest_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('forest_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Gamescom 2019", 'gamescom_2019_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('gamescom_2019_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Gearbox", 'gearbox_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('gearbox_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Golden Wheel", 'golden_wheel_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('golden_wheel_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Hyperion", 'hyperion_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('hyperion_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Jakobs", 'jakobs_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('jakobs_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Lifeline", 'lifeline_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('lifeline_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Lollipop", 'lollipop_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('lollipop_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Maliwan", 'maliwan_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('maliwan_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Ninja Shark", 'ninja_shark_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('ninja_shark_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Police", 'police_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('police_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Psycho", 'psycho_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('psycho_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Spicy Tuna Roll", 'spicy_tuna_roll_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('spicy_tuna_roll_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Stealth", 'stealth_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('stealth_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Torgue", 'torgue_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('torgue_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            Shot("Vladof", 'vladof_1_heavy_blade.jpg', 'heavy armor, blade wheel', variants=[
                Variant('vladof_2_regular_hover.jpg', 'light armor, hover wheel'),
                ]),
            ]))

vehicles.append(Collection('technical',
        'Technical Skins',
        'Technical Skin',
        'vehicle_skins/technical',
        'Mar 26, 2020',
        [
            Shot("Atlas", 'atlas_1_regular.jpg', 'light armor', variants=[
                Variant('atlas_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Blue Angels", 'blue_angels_1_regular.jpg', 'light armor', variants=[
                Variant('blue_angels_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Bubblegum", 'bubblegum_1_regular.jpg', 'light armor', variants=[
                Variant('bubblegum_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Children of the Vault", 'children_of_the_vault_1_regular.jpg', 'light armor', variants=[
                Variant('children_of_the_vault_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Dahl", 'dahl_1_regular.jpg', 'light armor', variants=[
                Variant('dahl_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Default", 'default_1_regular.jpg', 'light armor (default skin)', order=1, variants=[
                Variant('default_2_heavy.jpg', 'heavy armor (default skin)'),
                ]),
            Shot("E3 2019", 'e3_2019_1_regular.jpg', 'light armor', variants=[
                Variant('e3_2019_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Ellie", 'ellie_1_regular.jpg', 'light armor', variants=[
                Variant('ellie_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Festi-Flesh", 'festi-flesh_1_regular.jpg', 'light armor', variants=[
                Variant('festi-flesh_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Follow-Me", 'follow-me_1_regular.jpg', 'light armor', variants=[
                Variant('follow-me_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Forest Camo", 'forest_camo_1_regular.jpg', 'light armor', variants=[
                Variant('forest_camo_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Frost Rider", 'frost_rider_1_regular.jpg', 'light armor', variants=[
                Variant('frost_rider_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Gearbox", 'gearbox_1_regular.jpg', 'light armor', variants=[
                Variant('gearbox_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Golden Ticket", 'golden_ticket_1_regular.jpg', 'light armor', variants=[
                Variant('golden_ticket_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Halftone", 'halftone_1_regular.jpg', 'light armor', variants=[
                Variant('halftone_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Hyperion", 'hyperion_1_regular.jpg', 'light armor', variants=[
                Variant('hyperion_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("I like dinosaurs.", 'i_like_dinosaurs_1_regular.jpg', 'light armor', variants=[
                Variant('i_like_dinosaurs_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Jakobs", 'jakobs_1_regular.jpg', 'light armor', variants=[
                Variant('jakobs_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Leather", 'leather_1_regular.jpg', 'light armor', variants=[
                Variant('leather_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Magic Number", 'magic_number_1_regular.jpg', 'light armor', variants=[
                Variant('magic_number_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Maliwan", 'maliwan_1_regular.jpg', 'light armor', variants=[
                Variant('maliwan_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Maya", 'maya_1_regular.jpg', 'light armor', variants=[
                Variant('maya_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Plaid", 'plaid_1_regular.jpg', 'light armor', variants=[
                Variant('plaid_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Roadkill", 'roadkill_1_regular.jpg', 'light armor', variants=[
                Variant('roadkill_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Skag", 'skag_1_regular.jpg', 'light armor', variants=[
                Variant('skag_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Spicy Tuna Roll", 'spicy_tuna_roll_1_regular.jpg', 'light armor', variants=[
                Variant('spicy_tuna_roll_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Stealth", 'stealth_1_regular.jpg', 'light armor', variants=[
                Variant('stealth_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Tentacar", 'tentacar_1_regular.jpg', 'light armor', variants=[
                Variant('tentacar_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Thunderbird", 'thunderbird_1_regular.jpg', 'light armor', variants=[
                Variant('thunderbird_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Torgue", 'torgue_1_regular.jpg', 'light armor', variants=[
                Variant('torgue_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Vaughn's", 'vaughns_1_regular.jpg', 'light armor', variants=[
                Variant('vaughns_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Vladof", 'vladof_1_regular.jpg', 'light armor', variants=[
                Variant('vladof_2_heavy.jpg', 'heavy armor'),
                ]),
            Shot("Woodland Camo", 'woodland_camo_1_regular.jpg', 'light armor', variants=[
                Variant('woodland_camo_2_heavy.jpg', 'heavy armor'),
                ]),
            ]))

vehicles.append(Collection('jetbeast',
        'Jetbeast Skins',
        'Jetbeast Skin',
        'vehicle_skins/jetbeast',
        'Jun 30, 2020',
        [
            Shot('Beefy', 'beefy.jpg'),
            Shot('Company Car', 'company_car.jpg'),
            Shot('Default', 'default.jpg', '(default skin)', order=1),
            Shot('Devil Rider', 'devil_rider.jpg'),
            Shot('Reptile', 'reptile.jpg'),
            Shot('Woodsy', 'woodsy.jpg'),
            ]))

###
### Main rendering functions + such follow
###

def main(base_img_href, thumb_size, urls=False, verbose=False):
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

    # Loop through our categories and process 'em
    navigation = {
            'main': [
                # Actually, I don't think I want that link up there...
                #{'title': 'Home', 'url': '/'},
                ],
            'side': [
                {'title': 'Main Links', 'children': [
                    {'title': 'Home', 'url': '/'},
                    {'title': 'Changelog', 'url': '/changelog/'},
                    {'title': 'Original Imgur', 'url': '/original/'},
                    ]},
                ],
            }
    for category in categories:

        # Add the category to our sidebar
        new_cat = {'title': category.label, 'children': []}
        navigation['side'].append(new_cat)

        # Loop through collections and write those out
        for collection in category:

            # ... but first add the collection to our sidebar
            report_url = f'/{collection.slug}/'
            new_cat['children'].append({'title': collection.name_plural, 'url': report_url})

            # Now get to actually processing
            filename = collection.get_filename()
            print(f'Writing to {filename}...')
            with open(filename, 'w') as odf:

                # Header
                print('---', file=odf)
                print(f'title: {collection.name_plural}', file=odf)
                print(f'permalink: {report_url}', file=odf)
                print('---', file=odf)
                print('', file=odf)
                print(f'<h1>{collection.name_plural}</h1>', file=odf)
                print('', file=odf)

                # Last updated, and (if we have it) extra text
                print('<p class="last_updated"><strong>Last Updated:</strong> {}</p>'.format(collection.last_updated), file=odf)
                if collection.extra_text:
                    print('<p class="extra_text">{}</p>'.format(html.escape(collection.extra_text)), file=odf)
                print('', file=odf)

                # Report on the total count
                if len(collection) == 1:
                    report = collection.name_single
                else:
                    report = collection.name_plural
                print('<div class="cosmetic_count">Total {}: {}</div>'.format(
                    report,
                    len(collection),
                    ), file=odf)
                print('', file=odf)

                # Loop over shots
                if collection.grid:
                    print('<div class="grid-area">', file=odf)
                    print('', file=odf)
                for shot in sorted(collection):
                    shot.output(odf, collection, base_img_href, thumb_size, urls, verbose)
                if collection.grid:
                    print('</div>', file=odf)

    # Write out navigation
    print('Writing out navigation')
    with open('_data/navigation.yml', 'w') as odf:
        yaml.dump(navigation, odf, indent=2, default_flow_style=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
            description='Generate BL3 Cosmetics Archive',
            )

    parser.add_argument('-b', '--base-img-href',
            default='/bl3cosmetics',
            help='Base image HREF for locally-sourced images',
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

    main(args.base_img_href, (args.width, args.height), args.urls, args.verbose)

