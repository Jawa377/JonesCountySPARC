-- SPARC Textbook Studio: seed data (Phase 1 pilot)
--
-- 6th Grade Science, Unit 3, "Water in Earth's Systems" for Ms. Ruffin.
-- Text is verbatim from SPARC-Studio-Handout.pdf (pages 2 and 3).
-- Explicit ids so alignments can reference their elements.
--
-- NOTE: the handout marks its standard codes as illustrative. These five
-- descriptions are the handout's short forms, not official GaDOE text; real
-- CASE retrieval replaces them.

INSERT INTO teachers (teacher_id, name, email) VALUES
(1, 'Ms. Ruffin', 'ruffin@example.org'),
(2, 'Placeholder Teacher A', 'teacher.a@example.org'),
(3, 'Placeholder Teacher B', 'teacher.b@example.org');

INSERT INTO units (unit_id, teacher_id, subject, grade, unit_number, title, standards_set, lexile_min, lexile_max, voice) VALUES
(1, 1, 'Science', 6, 3, 'Water in Earth''s Systems', 'GSE Science Grade 6', 850, 950, 'match_materials');

INSERT INTO materials (material_id, unit_id, filename, file_type, size_label) VALUES
(1, 1, 'Water Cycle',   'PPTX', '18 slides'),
(2, 1, 'Ocmulgee Lab',  'DOCX', '3 pages'),
(3, 1, 'Unit 3 Pacing', 'DOCX', '2 pages'),
(4, 1, 'Density Lab',   'PDF',  '1 page'),
(5, 1, 'Vocab List',    'DOCX', '1 page');

INSERT INTO standards (standard_id, code, description, standards_set, source_url, framework) VALUES
(1, 'S6E3.a', 'Where water is located on Earth and its relative abundance in each reservoir.', 'GSE Science Grade 6', 'https://case.georgiastandards.org', 'GSE'),
(2, 'S6E3.b', 'Role of the sun''s energy in cycling water.', 'GSE Science Grade 6', 'https://case.georgiastandards.org', 'GSE'),
(3, 'S6E3.c', 'How human activity affects water quality and availability.', 'GSE Science Grade 6', 'https://case.georgiastandards.org', 'GSE'),
(4, 'S6E3.d', 'Evaluate methods for conserving and protecting water resources.', 'GSE Science Grade 6', 'https://case.georgiastandards.org', 'GSE'),
(5, 'S6E4.b', 'Transfer of heat energy from the sun to land and water.', 'GSE Science Grade 6', 'https://case.georgiastandards.org', 'GSE');

-- Section 1: the studio draft (page 2). word_count 1180 is the handout's figure.
INSERT INTO sections (section_id, unit_id, section_number, title, learning_target, body_text, word_count, lexile, duration_minutes, status) VALUES
(1, 1, 1, 'Why Water Runs the Planet', NULL,
'If you could shrink Earth to the size of a basketball, all of its water would fit into a single drop resting on the surface. That drop is thin, but almost nothing about the planet works without it.

## Water is almost never sitting still

The water in the Ocmulgee River did not start there. Some of it evaporated off the Gulf of Mexico, drifted north as vapor, and fell on Jones County as rain. Some soaked into the ground and traveled for years through soil and rock before seeping back to the surface.

## Why the coast stays mild

Water is stubborn about changing temperature. Sand, rock, and soil do the opposite — they heat fast and cool fast. That single difference explains why a beach burns your feet at noon while the ocean twenty steps away is still cold.

Scale it up and it stops being about your feet. Savannah sits on the coast; Macon sits inland. Both get roughly the same sunlight, but the Atlantic acts like a giant thermal cushion for Savannah — slow to warm in spring, slow to give up its heat in fall.

## What happens when the loop is interrupted

Every parking lot, roof, and road is a surface water cannot soak into. Rain that would have infiltrated instead runs across pavement, picking up oil and sediment, and arrives at the nearest creek fast, dirty, and all at once. This is why a neighborhood that floods today may not have flooded thirty years ago, even though the rainfall has not changed.',
1180, 910, NULL, 'draft');

-- Section 2: the finished lesson (page 3). word_count is the real count of the reading.
INSERT INTO sections (section_id, unit_id, section_number, title, learning_target, body_text, word_count, lexile, duration_minutes, status) VALUES
(2, 1, 2, 'Why the Coast Stays Mild',
'I can explain why water heats and cools more slowly than land, and use that to predict how living near the ocean changes a town''s temperature across the year.',
'Water is stubborn about changing temperature. It takes a great deal of energy to warm it up, and it gives that energy back slowly on the way down. Sand, rock, and soil do the opposite — they heat fast and cool fast.

That single difference explains something you have felt. At the beach in July, the sand burns your feet at noon while the ocean twenty steps away is still cold enough to make you flinch. Same sun, same hours, completely different result.

Scale it up and it stops being about your feet. Savannah sits on the coast; Macon sits inland. Both get roughly the same sunlight, but the Atlantic acts like a giant thermal cushion for Savannah — slow to warm in spring, slow to give up its heat in fall. Macon has no such cushion, so its summers run hotter and its winters run colder. The ocean is not changing the amount of energy arriving. It is changing how fast that energy shows up as temperature.',
168, 910, 45, 'draft');

INSERT INTO vocab_terms (vocab_term_id, section_id, term, definition, sort_order) VALUES
(1, 2, 'Specific heat', 'How much energy a material needs to raise its temperature. Water''s is unusually high, which is why it resists warming.', 1),
(2, 2, 'Thermal cushion', 'A large body of water that slows temperature swings in the land nearby.', 2);

INSERT INTO assignments (assignment_id, section_id, level, prompt_text) VALUES
(1, 2, 'support', 'Using our two-pan data table, circle which line rose faster: water or sand. Write one sentence saying which one holds its heat longer.'),
(2, 2, 'core', 'Graph the temperature of water and sand over 30 minutes. Then write a paragraph predicting whether Savannah or Macon has the larger swing between July and January, using your graph as evidence.'),
(3, 2, 'extension', 'Lake Sinclair is far smaller than the Atlantic. Argue in one paragraph whether it produces a measurable cushion effect for Milledgeville, and say what data you''d need to prove it.');

INSERT INTO quiz_items (quiz_item_id, section_id, dok_level, prompt_text) VALUES
(1, 2, 3, 'A student pours 100 mL of water and 100 mL of sand into identical pans and sets both in the sun. Predict which warms faster and explain what that means for a coastal town compared to an inland one.');

-- Coverage for Unit 3. Rolled up per standard: S6E3.a covered, S6E4.b covered,
-- S6E3.c partial, S6E3.b gap, S6E3.d gap  ->  "2 covered, 1 partial, 2 gaps".
-- evidence_text must match the element text exactly so the studio can highlight it.
INSERT INTO alignments (alignment_id, unit_id, standard_id, element_type, element_id, coverage_status, evidence_text, evidence_note) VALUES
(1, 1, 1, 'section', 1, 'covered',
 'If you could shrink Earth to the size of a basketball, all of its water would fit into a single drop resting on the surface. That drop is thin, but almost nothing about the planet works without it.',
 NULL),
(2, 1, 5, 'section', 1, 'covered',
 'Water is stubborn about changing temperature. Sand, rock, and soil do the opposite — they heat fast and cool fast. That single difference explains why a beach burns your feet at noon while the ocean twenty steps away is still cold.',
 NULL),
(3, 1, 3, 'section', 1, 'partial',
 'Every parking lot, roof, and road is a surface water cannot soak into. Rain that would have infiltrated instead runs across pavement, picking up oil and sediment, and arrives at the nearest creek fast, dirty, and all at once. This is why a neighborhood that floods today may not have flooded thirty years ago, even though the rainfall has not changed.',
 'Explains runoff, but no item asks for a solution'),
(4, 1, 2, NULL, NULL, 'gap', NULL, 'Nothing covers it'),
(5, 1, 4, NULL, NULL, 'gap', NULL, 'Planned for Section 2'),
(6, 1, 5, 'section', 2, 'covered',
 'Water is stubborn about changing temperature. It takes a great deal of energy to warm it up, and it gives that energy back slowly on the way down.',
 NULL),
(7, 1, 5, 'assignment', 1, 'covered', NULL, NULL),
(8, 1, 5, 'assignment', 2, 'covered', NULL, NULL),
(9, 1, 5, 'assignment', 3, 'covered', NULL, NULL),
(10, 1, 5, 'quiz_item', 1, 'covered', NULL, NULL);
