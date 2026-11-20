<?php
// Columns named *_id with no foreign key, and whether an index covers them (MySQL or MariaDB).
// Run from the Laravel repo, never without --execute and the closed stdin (tinker hangs otherwise):
//   php artisan tinker --execute="require '<this file>';" < /dev/null
// Read-only: it queries information_schema for the connection's own database.
// A missing foreign key is a finding only after a read: polymorphic ids, ids of another system and
// columns kept on purpose after a delete are legitimate.
$db = DB::selectOne('SELECT DATABASE() AS d')->d;
$rows = DB::select("SELECT c.TABLE_NAME t, c.COLUMN_NAME col, (SELECT COUNT(*) FROM information_schema.STATISTICS s WHERE s.TABLE_SCHEMA=c.TABLE_SCHEMA AND s.TABLE_NAME=c.TABLE_NAME AND s.COLUMN_NAME=c.COLUMN_NAME AND s.SEQ_IN_INDEX=1) idx FROM information_schema.COLUMNS c LEFT JOIN information_schema.KEY_COLUMN_USAGE k ON k.TABLE_SCHEMA=c.TABLE_SCHEMA AND k.TABLE_NAME=c.TABLE_NAME AND k.COLUMN_NAME=c.COLUMN_NAME AND k.REFERENCED_TABLE_NAME IS NOT NULL WHERE c.TABLE_SCHEMA=? AND c.COLUMN_NAME LIKE '%\\_id' AND k.COLUMN_NAME IS NULL ORDER BY t, col", [$db]);
$all = DB::selectOne("SELECT COUNT(*) n FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=? AND COLUMN_NAME LIKE '%\\_id'", [$db])->n;
$tables = DB::selectOne("SELECT COUNT(*) n FROM information_schema.TABLES WHERE TABLE_SCHEMA=?", [$db])->n;
$bare = array_filter($rows, fn ($r) => !$r->idx);
$name = fn ($r) => "$r->t.$r->col";
echo "database $db: $tables tables; $all *_id columns; " . count($rows) . " without a foreign key; of those " . count($bare) . " without an index\n";
echo "no foreign key, no index: " . implode(' ', array_map($name, $bare)) . "\n";
echo "no foreign key, indexed: " . implode(' ', array_map($name, array_filter($rows, fn ($r) => $r->idx))) . "\n";
