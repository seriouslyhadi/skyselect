package com.example.skyselect;

/** One selectable sky. {@code id} must match a folder in resources/resourcepacks/. */
public enum SkyPreset {
    NORTHERN_LIGHTS("northern_lights", "Northern Lights", "Flowing green-to-violet aurora curtains."),
    CRIMSON_AURORA("crimson_aurora", "Crimson Aurora", "Rare red and magenta aurora."),
    METEOR_SHOWER("meteor_shower", "Meteor Shower", "Bright stars with streaking meteors."),
    POLAR_NIGHT("polar_night", "Polar Night", "Aurora curtains AND a meteor shower."),
    COSMIC_NEBULA("cosmic_nebula", "Cosmic Nebula", "Purple/blue nebula, stars, a few meteors."),
    LAYOUT_TEST("layout_test", "[Debug] Layout Test", "Labelled cube faces, always visible. For checking orientation.");

    public final String id;
    public final String displayName;
    public final String description;

    SkyPreset(String id, String displayName, String description) {
        this.id = id;
        this.displayName = displayName;
        this.description = description;
    }
}
