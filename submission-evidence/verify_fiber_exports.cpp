// Verification helper: baseline network codec versus the single-object file exporter.
#include "vc_object_store/objects/FiberJson.hpp"
#include "vc_object_store/objects/GeometryExport.hpp"
#include <fstream>
#include <iostream>

int main(int argc, char** argv) try {
    if (argc != 4) throw std::runtime_error("usage: verify_fiber_exports network|individual DB NEW_OUTPUT_DIR");
    const std::string mode = argv[1];
    if (mode != "network" && mode != "individual") throw std::runtime_error("invalid export mode");
    const std::filesystem::path output = argv[3];
    if (!std::filesystem::create_directory(output)) throw std::runtime_error("output directory already exists");
    vc::objects::OpenOptions options; options.readOnly = true;
    auto db = vc::objects::ObjectStore::open(argv[2], options);
    std::vector<std::string> ids;
    {
        auto read = db.read();
        vc::objects::RevisionSelection selection;
        for (const auto& object : db.objectsByKind(read, "fiber")) {
            ids.push_back(object.uuid);
            selection[object.uuid] = db.currentObjectRevision(read, object.uuid)->uuid;
        }
        if (mode == "network") {
            const auto network = vc::objects::fiberNetworkJson(db, read, selection);
            for (const auto& [uuid, document] : network) {
                std::ofstream file(output / (uuid + ".json"));
                file.exceptions(std::ios::badbit | std::ios::failbit);
                file << document << '\n';
                file.close();
            }
        }
    }
    if (mode == "individual")
        for (const auto& uuid : ids) vc::objects::exportGeometry(db, uuid, output / (uuid + ".json"));
    std::cout << ids.size() << " fibers exported (" << mode << ")\n";
    return 0;
} catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
