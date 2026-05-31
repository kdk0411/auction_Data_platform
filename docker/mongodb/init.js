db = db.getSiblingDB("auction_db");

db.createCollection("item_instances", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["item_id", "item_type", "base_effects", "current_effects", "remaining_slots", "created_at"],
            properties: {
                item_id:         { bsonType: "int" },
                item_name:       { bsonType: "string" },
                item_type:       { enum: ["equipment", "consumable", "etc"] },
                category_sub:    { bsonType: "string" },
                icon_url:        { bsonType: "string" },
                base_effects:    { bsonType: "object" },
                current_effects: { bsonType: "object" },
                applied_scrolls: { bsonType: "array" },
                remaining_slots: { bsonType: "int", minimum: 0 },
                is_enhanced:     { bsonType: "bool" },
                created_at:      { bsonType: "date" }
            }
        }
    }
});

db.item_instances.createIndex({ item_id: 1 });
db.item_instances.createIndex({ item_id: 1, remaining_slots: 1 });
db.item_instances.createIndex({ is_enhanced: 1 });
db.item_instances.createIndex({ created_at: -1 });

db.item_instances.createIndex({ "current_effects.str":          1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.dex":          1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.int":          1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.luk":          1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.phys_attack":  1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.mag_attack":   1 }, { sparse: true });
db.item_instances.createIndex({ "current_effects.phys_defense": 1 }, { sparse: true });

print("auction_db initialized.");
